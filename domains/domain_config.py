"""Domain Configuration System for EJE.

Provides unified configuration management for domain-specific settings,
enabling seamless domain switching and dynamic critic loading.
"""

import yaml
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class DomainType(Enum):
    """Supported domain types."""
    HEALTHCARE = "healthcare"
    FINANCIAL = "financial"
    EDUCATION = "education"
    LEGAL = "legal"


@dataclass
class DomainProfile:
    """Domain-specific configuration profile."""
    name: str
    domain_type: DomainType
    description: str
    
    # Critic configuration
    critics: List[str] = field(default_factory=list)
    critic_config: Dict[str, Any] = field(default_factory=dict)
    
    # Precedent configuration
    precedent_namespaces: List[str] = field(default_factory=list)
    precedent_config: Dict[str, Any] = field(default_factory=dict)
    
    # Regulatory configuration
    regulatory_frameworks: List[str] = field(default_factory=list)
    compliance_requirements: Dict[str, Any] = field(default_factory=dict)
    
    # Inheritance
    inherits_from: Optional[str] = None
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=dict)
    
    # Metadata
    version: str = "1.0.0"
    author: str = "EJE Team"
    tags: List[str] = field(default_factory=list)


class DomainConfigurationError(Exception):
    """Raised when domain configuration fails."""
    pass


class DomainConfigurationSystem:
    """Manages domain-specific configurations and profile loading."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the domain configuration system.
        
        Args:
            config_dir: Directory containing domain profile YAML files.
                       Defaults to domains/profiles/
        """
        if config_dir is None:
            # Default to domains/profiles directory
            config_dir = Path(__file__).parent / "profiles"
        
        self.config_dir = Path(config_dir)
        self.profiles: Dict[str, DomainProfile] = {}
        self.active_profile: Optional[DomainProfile] = None
        self._loaded_critics: Dict[str, Any] = {}
        
    def load_profile(self, profile_name: str) -> DomainProfile:
        """
        Load a domain profile from YAML file.
        
        Args:
            profile_name: Name of the profile (without .yaml extension)
            
        Returns:
            Loaded DomainProfile instance
            
        Raises:
            DomainConfigurationError: If profile cannot be loaded
        """
        profile_path = self.config_dir / f"{profile_name}.yaml"
        
        if not profile_path.exists():
            raise DomainConfigurationError(
                f"Profile not found: {profile_path}"
            )
        
        try:
            with open(profile_path, 'r') as f:
                profile_data = yaml.safe_load(f)
            
            # Handle inheritance
            if 'inherits_from' in profile_data and profile_data['inherits_from']:
                parent_profile = self.load_profile(profile_data['inherits_from'])
                profile_data = self._merge_profiles(parent_profile, profile_data)
            
            # Validate and create profile
            profile = self._create_profile(profile_data)
            self.profiles[profile_name] = profile
            
            return profile
            
        except yaml.YAMLError as e:
            raise DomainConfigurationError(
                f"Invalid YAML in profile {profile_name}: {e}"
            )
        except Exception as e:
            raise DomainConfigurationError(
                f"Failed to load profile {profile_name}: {e}"
            )
    
    def _create_profile(self, data: Dict[str, Any]) -> DomainProfile:
        """
        Create a DomainProfile from dictionary data.
        
        Args:
            data: Profile configuration dictionary
            
        Returns:
            DomainProfile instance
        """
        # Convert domain_type string to enum
        domain_type_str = data.get('domain_type', 'healthcare').upper()
        try:
            domain_type = DomainType(domain_type_str.lower())
        except ValueError:
            raise DomainConfigurationError(
                f"Invalid domain type: {domain_type_str}"
            )
        
        return DomainProfile(
            name=data['name'],
            domain_type=domain_type,
            description=data.get('description', ''),
            critics=data.get('critics', []),
            critic_config=data.get('critic_config', {}),
            precedent_namespaces=data.get('precedent_namespaces', []),
            precedent_config=data.get('precedent_config', {}),
            regulatory_frameworks=data.get('regulatory_frameworks', []),
            compliance_requirements=data.get('compliance_requirements', {}),
            inherits_from=data.get('inherits_from'),
            features=data.get('features', {}),
            version=data.get('version', '1.0.0'),
            author=data.get('author', 'EJE Team'),
            tags=data.get('tags', [])
        )
    
    def _merge_profiles(self, parent: DomainProfile, child_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge parent profile with child profile data (inheritance).
        
        Args:
            parent: Parent DomainProfile
            child_data: Child profile data dictionary
            
        Returns:
            Merged profile data dictionary
        """
        # Start with parent data
        merged = {
            'name': child_data.get('name', parent.name),
            'domain_type': child_data.get('domain_type', parent.domain_type.value),
            'description': child_data.get('description', parent.description),
            'version': child_data.get('version', parent.version),
            'author': child_data.get('author', parent.author),
        }
        
        # Merge lists (union)
        merged['critics'] = list(set(parent.critics + child_data.get('critics', [])))
        merged['precedent_namespaces'] = list(set(
            parent.precedent_namespaces + child_data.get('precedent_namespaces', [])
        ))
        merged['regulatory_frameworks'] = list(set(
            parent.regulatory_frameworks + child_data.get('regulatory_frameworks', [])
        ))
        merged['tags'] = list(set(parent.tags + child_data.get('tags', [])))
        
        # Merge dictionaries (child overrides parent)
        merged['critic_config'] = {**parent.critic_config, **child_data.get('critic_config', {})}
        merged['precedent_config'] = {**parent.precedent_config, **child_data.get('precedent_config', {})}
        merged['compliance_requirements'] = {
            **parent.compliance_requirements,
            **child_data.get('compliance_requirements', {})
        }
        merged['features'] = {**parent.features, **child_data.get('features', {})}
        
        return merged
    
    def switch_domain(self, profile_name: str) -> None:
        """
        Switch active domain profile.
        
        Args:
            profile_name: Name of profile to activate
            
        Raises:
            DomainConfigurationError: If profile doesn't exist
        """
        if profile_name not in self.profiles:
            self.load_profile(profile_name)
        
        self.active_profile = self.profiles[profile_name]
        self._loaded_critics.clear()  # Clear cached critics
        
    def load_critics(self) -> List[Any]:
        """
        Dynamically load critics for the active domain.
        
        Returns:
            List of loaded critic classes
            
        Raises:
            DomainConfigurationError: If no active profile or critic loading fails
        """
        if not self.active_profile:
            raise DomainConfigurationError("No active profile set")
        
        critics = []
        domain_module = self.active_profile.domain_type.value
        
        for critic_name in self.active_profile.critics:
            if critic_name in self._loaded_critics:
                critics.append(self._loaded_critics[critic_name])
                continue
            
            try:
                # Import from domain-specific module
                module_path = f"domains.{domain_module}.{domain_module}_critics"
                module = importlib.import_module(module_path)
                
                # Get critic class
                critic_class = getattr(module, critic_name)
                critics.append(critic_class)
                self._loaded_critics[critic_name] = critic_class
                
            except (ImportError, AttributeError) as e:
                raise DomainConfigurationError(
                    f"Failed to load critic {critic_name}: {e}"
                )
        
        return critics
    
    def validate_profile(self, profile: DomainProfile) -> bool:
        """
        Validate a domain profile for correctness.
        
        Args:
            profile: Profile to validate
            
        Returns:
            True if valid
            
        Raises:
            DomainConfigurationError: If validation fails
        """
        # Check required fields
        if not profile.name:
            raise DomainConfigurationError("Profile name is required")
        
        if not profile.description:
            raise DomainConfigurationError("Profile description is required")
        
        # Check for cross-domain contamination
        domain_prefix = profile.domain_type.value
        for critic in profile.critics:
            if not critic.startswith(domain_prefix.capitalize()):
                # Allow generic critics
                if not critic.startswith('Generic'):
                    raise DomainConfigurationError(
                        f"Critic {critic} does not match domain {domain_prefix}"
                    )
        
        # Validate precedent namespaces
        for namespace in profile.precedent_namespaces:
            if not namespace.startswith(domain_prefix):
                raise DomainConfigurationError(
                    f"Precedent namespace {namespace} does not match domain {domain_prefix}"
                )
        
        return True
    
    def get_active_profile(self) -> Optional[DomainProfile]:
        """Get the currently active domain profile."""
        return self.active_profile
    
    def list_profiles(self) -> List[str]:
        """List all available profile names."""
        if not self.config_dir.exists():
            return []
        
        return [
            p.stem for p in self.config_dir.glob('*.yaml')
        ]
    
    def export_profile(self, profile: DomainProfile, output_path: Path) -> None:
        """
        Export a profile to YAML file.
        
        Args:
            profile: Profile to export
            output_path: Path to write YAML file
        """
        data = {
            'name': profile.name,
            'domain_type': profile.domain_type.value,
            'description': profile.description,
            'critics': profile.critics,
            'critic_config': profile.critic_config,
            'precedent_namespaces': profile.precedent_namespaces,
            'precedent_config': profile.precedent_config,
            'regulatory_frameworks': profile.regulatory_frameworks,
            'compliance_requirements': profile.compliance_requirements,
            'inherits_from': profile.inherits_from,
            'features': profile.features,
            'version': profile.version,
            'author': profile.author,
            'tags': profile.tags
        }
        
        with open(output_path, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


# Singleton instance
_config_system: Optional[DomainConfigurationSystem] = None


def get_config_system() -> DomainConfigurationSystem:
    """Get the global domain configuration system instance."""
    global _config_system
    if _config_system is None:
        _config_system = DomainConfigurationSystem()
    return _config_system
