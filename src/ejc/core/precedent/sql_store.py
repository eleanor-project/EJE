"""
SQL-based Precedent Storage Backend

Provides production-grade precedent storage using SQLAlchemy with support
for both SQLite and PostgreSQL backends. Implements efficient querying,
indexing, and relationship management for precedent cases.

Features:
- Support for SQLite (development) and PostgreSQL (production)
- Full CRUD operations for precedents
- Efficient indexing for fast lookups
- Relationship tracking between precedents
- Transaction support for data integrity
- Migration utilities for JSON legacy data
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import NullPool

from ...utils.logging import get_logger
from ..error_handling import PrecedentException, ConfigurationException


logger = get_logger("ejc.precedent.sql_store")

Base = declarative_base()


# Database Models

class Precedent(Base):
    """Precedent case stored in SQL database"""
    __tablename__ = 'precedents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_hash = Column(String(64), nullable=False, unique=True, index=True)
    request_id = Column(String(128), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Input data
    input_text = Column(Text, nullable=False)
    input_context = Column(Text)  # JSON string
    input_metadata = Column(Text)  # JSON string

    # Final decision
    final_verdict = Column(String(32), nullable=False, index=True)
    final_reason = Column(Text)
    avg_confidence = Column(Float)
    ambiguity = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    critic_outputs = relationship("CriticOutput", back_populates="precedent", cascade="all, delete-orphan")
    embedding = relationship("PrecedentEmbedding", back_populates="precedent", uselist=False, cascade="all, delete-orphan")
    references_from = relationship("PrecedentReference", foreign_keys="PrecedentReference.precedent_id", back_populates="precedent", cascade="all, delete-orphan")
    references_to = relationship("PrecedentReference", foreign_keys="PrecedentReference.referenced_precedent_id", back_populates="referenced_precedent")

    # Indexes
    __table_args__ = (
        Index('idx_precedent_timestamp_verdict', 'timestamp', 'final_verdict'),
        Index('idx_precedent_created', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert precedent to dictionary"""
        return {
            'id': self.id,
            'case_hash': self.case_hash,
            'request_id': self.request_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'input': {
                'text': self.input_text,
                'context': json.loads(self.input_context) if self.input_context else {},
                'metadata': json.loads(self.input_metadata) if self.input_metadata else {}
            },
            'final_decision': {
                'overall_verdict': self.final_verdict,
                'reason': self.final_reason,
                'avg_confidence': self.avg_confidence,
                'ambiguity': self.ambiguity
            },
            'critic_outputs': [co.to_dict() for co in self.critic_outputs] if self.critic_outputs else [],
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CriticOutput(Base):
    """Critic evaluation output for a precedent"""
    __tablename__ = 'critic_outputs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    precedent_id = Column(Integer, ForeignKey('precedents.id', ondelete='CASCADE'), nullable=False, index=True)

    critic_name = Column(String(128), nullable=False, index=True)
    verdict = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False)
    justification = Column(Text)
    weight = Column(Float, default=1.0)
    priority = Column(String(32))

    # Relationships
    precedent = relationship("Precedent", back_populates="critic_outputs")

    # Indexes
    __table_args__ = (
        Index('idx_critic_precedent_name', 'precedent_id', 'critic_name'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert critic output to dictionary"""
        return {
            'critic': self.critic_name,
            'verdict': self.verdict,
            'confidence': self.confidence,
            'justification': self.justification,
            'weight': self.weight,
            'priority': self.priority
        }


class PrecedentEmbedding(Base):
    """Vector embedding for semantic similarity search"""
    __tablename__ = 'precedent_embeddings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    precedent_id = Column(Integer, ForeignKey('precedents.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)

    embedding = Column(LargeBinary, nullable=False)  # Pickled numpy array
    model_name = Column(String(128), default='all-MiniLM-L6-v2')
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    precedent = relationship("Precedent", back_populates="embedding")


class PrecedentReference(Base):
    """Tracks relationships between precedents"""
    __tablename__ = 'precedent_references'

    id = Column(Integer, primary_key=True, autoincrement=True)
    precedent_id = Column(Integer, ForeignKey('precedents.id', ondelete='CASCADE'), nullable=False, index=True)
    referenced_precedent_id = Column(Integer, ForeignKey('precedents.id', ondelete='CASCADE'), nullable=False, index=True)

    similarity_score = Column(Float)
    reference_type = Column(String(32), default='semantic')  # semantic, structural, outcome
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    precedent = relationship("Precedent", foreign_keys=[precedent_id], back_populates="references_from")
    referenced_precedent = relationship("Precedent", foreign_keys=[referenced_precedent_id], back_populates="references_to")

    # Indexes
    __table_args__ = (
        Index('idx_reference_pair', 'precedent_id', 'referenced_precedent_id'),
        UniqueConstraint('precedent_id', 'referenced_precedent_id', 'reference_type', name='uq_precedent_reference'),
    )


class SQLPrecedentStore:
    """
    SQL-based precedent storage backend using SQLAlchemy.

    Supports both SQLite (development/testing) and PostgreSQL (production).
    Provides efficient storage, retrieval, and querying of precedent cases.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SQL precedent store.

        Args:
            config: Configuration dict containing:
                - db_url: SQLAlchemy database URL (e.g., "sqlite:///precedents.db" or "postgresql://...")
                - pool_size: Connection pool size (default: 5)
                - max_overflow: Max overflow connections (default: 10)
                - echo: Enable SQL logging (default: False)

        Raises:
            ConfigurationException: If configuration is invalid
        """
        try:
            self.config = config

            # Database URL
            self.db_url = config.get('db_url')
            if not self.db_url:
                raise ConfigurationException("Missing 'db_url' in SQL store configuration")

            # Connection pool settings (ignored for SQLite)
            pool_size = config.get('pool_size', 5)
            max_overflow = config.get('max_overflow', 10)
            echo = config.get('echo', False)

            # Create engine
            if self.db_url.startswith('sqlite'):
                # SQLite-specific settings
                self.engine = create_engine(
                    self.db_url,
                    echo=echo,
                    poolclass=NullPool,  # SQLite doesn't support connection pooling well
                    connect_args={'check_same_thread': False}
                )
            else:
                # PostgreSQL/other databases
                self.engine = create_engine(
                    self.db_url,
                    echo=echo,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    pool_pre_ping=True  # Test connections before using
                )

            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

            # Initialize database schema
            self._initialize_schema()

            logger.info(f"SQLPrecedentStore initialized with database: {self._safe_url()}")

        except Exception as e:
            raise ConfigurationException(f"Failed to initialize SQL precedent store: {str(e)}")

    def _safe_url(self) -> str:
        """Return database URL with credentials masked"""
        if '@' in self.db_url:
            # Mask credentials in connection string
            parts = self.db_url.split('@')
            return f"***@{parts[1]}"
        return self.db_url if not self.db_url.startswith('sqlite') else "sqlite:///<path>"

    def _initialize_schema(self):
        """Create database tables if they don't exist"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {str(e)}")
            raise

    @contextmanager
    def get_session(self) -> Session:
        """
        Get a database session with automatic cleanup.

        Yields:
            SQLAlchemy Session object
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _compute_case_hash(self, input_text: str, input_context: Dict[str, Any]) -> str:
        """Compute deterministic hash for a case"""
        content = f"{input_text}::{json.dumps(input_context, sort_keys=True)}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def store_precedent(
        self,
        request_id: str,
        input_text: str,
        input_context: Optional[Dict[str, Any]] = None,
        input_metadata: Optional[Dict[str, Any]] = None,
        final_verdict: str = '',
        final_reason: Optional[str] = None,
        avg_confidence: Optional[float] = None,
        ambiguity: Optional[float] = None,
        critic_outputs: Optional[List[Dict[str, Any]]] = None,
        embedding: Optional[bytes] = None,
        embedding_model: str = 'all-MiniLM-L6-v2',
        timestamp: Optional[datetime] = None
    ) -> int:
        """
        Store a new precedent case in the database.

        Args:
            request_id: Unique request identifier
            input_text: Input text for the case
            input_context: Additional context information
            input_metadata: Metadata about the input
            final_verdict: Final decision verdict
            final_reason: Reason for the decision
            avg_confidence: Average confidence across critics
            ambiguity: Ambiguity score
            critic_outputs: List of critic evaluations
            embedding: Serialized embedding vector
            embedding_model: Name of embedding model used
            timestamp: Case timestamp (defaults to now)

        Returns:
            Precedent ID

        Raises:
            PrecedentException: If storage fails
        """
        try:
            with self.get_session() as session:
                # Compute case hash
                case_hash = self._compute_case_hash(input_text, input_context or {})

                # Check if precedent already exists
                existing = session.query(Precedent).filter_by(case_hash=case_hash).first()
                if existing:
                    logger.warning(f"Precedent with hash {case_hash} already exists (ID: {existing.id})")
                    return existing.id

                # Create precedent
                precedent = Precedent(
                    case_hash=case_hash,
                    request_id=request_id,
                    timestamp=timestamp or datetime.utcnow(),
                    input_text=input_text,
                    input_context=json.dumps(input_context) if input_context else None,
                    input_metadata=json.dumps(input_metadata) if input_metadata else None,
                    final_verdict=final_verdict,
                    final_reason=final_reason,
                    avg_confidence=avg_confidence,
                    ambiguity=ambiguity
                )

                session.add(precedent)
                session.flush()  # Get precedent ID

                # Add critic outputs
                if critic_outputs:
                    for output in critic_outputs:
                        critic_output = CriticOutput(
                            precedent_id=precedent.id,
                            critic_name=output.get('critic', ''),
                            verdict=output.get('verdict', ''),
                            confidence=output.get('confidence', 0.0),
                            justification=output.get('justification'),
                            weight=output.get('weight', 1.0),
                            priority=output.get('priority')
                        )
                        session.add(critic_output)

                # Add embedding if provided
                if embedding:
                    precedent_embedding = PrecedentEmbedding(
                        precedent_id=precedent.id,
                        embedding=embedding,
                        model_name=embedding_model
                    )
                    session.add(precedent_embedding)

                session.commit()

                logger.info(f"Stored precedent {request_id} (ID: {precedent.id})")
                return precedent.id

        except Exception as e:
            logger.error(f"Failed to store precedent: {str(e)}")
            raise PrecedentException(f"Precedent storage failed: {str(e)}")

    def get_precedent(self, precedent_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a precedent by ID.

        Args:
            precedent_id: Precedent ID

        Returns:
            Precedent dictionary or None if not found
        """
        try:
            with self.get_session() as session:
                precedent = session.query(Precedent).filter_by(id=precedent_id).first()
                if precedent:
                    return precedent.to_dict()
                return None

        except Exception as e:
            logger.error(f"Failed to retrieve precedent {precedent_id}: {str(e)}")
            return None

    def query_precedents(
        self,
        verdict: Optional[str] = None,
        min_confidence: Optional[float] = None,
        max_ambiguity: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query precedents with filters.

        Args:
            verdict: Filter by verdict
            min_confidence: Minimum average confidence
            max_ambiguity: Maximum ambiguity score
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            List of precedent dictionaries
        """
        try:
            with self.get_session() as session:
                query = session.query(Precedent)

                if verdict:
                    query = query.filter(Precedent.final_verdict == verdict)
                if min_confidence is not None:
                    query = query.filter(Precedent.avg_confidence >= min_confidence)
                if max_ambiguity is not None:
                    query = query.filter(Precedent.ambiguity <= max_ambiguity)

                query = query.order_by(Precedent.timestamp.desc())
                query = query.limit(limit).offset(offset)

                return [p.to_dict() for p in query.all()]

        except Exception as e:
            logger.error(f"Failed to query precedents: {str(e)}")
            return []

    def add_precedent_reference(
        self,
        precedent_id: int,
        referenced_id: int,
        similarity_score: float,
        reference_type: str = 'semantic'
    ) -> bool:
        """
        Add a reference between two precedents.

        Args:
            precedent_id: Source precedent ID
            referenced_id: Referenced precedent ID
            similarity_score: Similarity score
            reference_type: Type of reference (semantic, structural, outcome)

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                # Check if reference already exists
                existing = session.query(PrecedentReference).filter_by(
                    precedent_id=precedent_id,
                    referenced_precedent_id=referenced_id,
                    reference_type=reference_type
                ).first()

                if existing:
                    # Update similarity score
                    existing.similarity_score = similarity_score
                else:
                    # Create new reference
                    reference = PrecedentReference(
                        precedent_id=precedent_id,
                        referenced_precedent_id=referenced_id,
                        similarity_score=similarity_score,
                        reference_type=reference_type
                    )
                    session.add(reference)

                session.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to add precedent reference: {str(e)}")
            return False

    def get_similar_precedents(
        self,
        precedent_id: int,
        reference_type: Optional[str] = None,
        min_similarity: float = 0.0,
        limit: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Get precedents similar to a given precedent.

        Args:
            precedent_id: Source precedent ID
            reference_type: Filter by reference type
            min_similarity: Minimum similarity score
            limit: Maximum results

        Returns:
            List of (precedent_dict, similarity_score) tuples
        """
        try:
            with self.get_session() as session:
                query = session.query(Precedent, PrecedentReference.similarity_score).join(
                    PrecedentReference,
                    Precedent.id == PrecedentReference.referenced_precedent_id
                ).filter(
                    PrecedentReference.precedent_id == precedent_id,
                    PrecedentReference.similarity_score >= min_similarity
                )

                if reference_type:
                    query = query.filter(PrecedentReference.reference_type == reference_type)

                query = query.order_by(PrecedentReference.similarity_score.desc()).limit(limit)

                return [(p.to_dict(), score) for p, score in query.all()]

        except Exception as e:
            logger.error(f"Failed to get similar precedents: {str(e)}")
            return []

    def count_precedents(self) -> int:
        """
        Get total count of precedents in database.

        Returns:
            Number of precedents
        """
        try:
            with self.get_session() as session:
                return session.query(Precedent).count()
        except Exception as e:
            logger.error(f"Failed to count precedents: {str(e)}")
            return 0

    def delete_precedent(self, precedent_id: int) -> bool:
        """
        Delete a precedent and all associated data.

        Args:
            precedent_id: Precedent ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_session() as session:
                precedent = session.query(Precedent).filter_by(id=precedent_id).first()
                if precedent:
                    session.delete(precedent)
                    session.commit()
                    logger.info(f"Deleted precedent {precedent_id}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Failed to delete precedent {precedent_id}: {str(e)}")
            return False

    def close(self):
        """Close database connections"""
        try:
            self.engine.dispose()
            logger.info("SQL precedent store closed")
        except Exception as e:
            logger.error(f"Error closing SQL store: {str(e)}")


# Convenience functions

def create_sql_store(db_url: str, **kwargs) -> SQLPrecedentStore:
    """
    Create a SQL precedent store with given database URL.

    Args:
        db_url: SQLAlchemy database URL
        **kwargs: Additional configuration options

    Returns:
        Configured SQLPrecedentStore instance
    """
    config = {'db_url': db_url, **kwargs}
    return SQLPrecedentStore(config)


def create_sqlite_store(db_path: str = 'precedents.db', **kwargs) -> SQLPrecedentStore:
    """
    Create a SQLite-based precedent store.

    Args:
        db_path: Path to SQLite database file
        **kwargs: Additional configuration options

    Returns:
        Configured SQLPrecedentStore instance
    """
    db_url = f"sqlite:///{db_path}"
    return create_sql_store(db_url, **kwargs)


def create_postgres_store(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    **kwargs
) -> SQLPrecedentStore:
    """
    Create a PostgreSQL-based precedent store.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        username: Database username
        password: Database password
        **kwargs: Additional configuration options

    Returns:
        Configured SQLPrecedentStore instance
    """
    db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    return create_sql_store(db_url, **kwargs)
