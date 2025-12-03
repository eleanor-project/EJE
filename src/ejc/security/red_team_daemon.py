"""
Red Team Daemon for EJE

Continuous background red team process for ongoing security validation with
randomized attack execution, production-safe testing, and real-time alerting.

Implements Issue #176: Implement Red Team Daemon

Features:
- Background continuous testing
- Randomized attack selection and timing
- Production-safe mode with throttling
- Real-time alerts on successful attacks
- Attack sophistication escalation
- Comprehensive logging and reporting
- Minimal resource usage
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time
import random
import logging
from enum import Enum
from pathlib import Path
import json

from .attack_patterns import AttackPatternLibrary, AttackPattern, AttackSeverity
from .adversarial_testing import TestResult, TestStatus


class DaemonMode(Enum):
    """Red team daemon operating modes."""
    DEVELOPMENT = "development"    # Full speed, all attacks
    STAGING = "staging"           # Moderate speed, high-severity attacks
    PRODUCTION = "production"     # Throttled, critical attacks only


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"           # Informational only
    WARNING = "warning"     # Minor vulnerability
    CRITICAL = "critical"   # Major vulnerability
    EMERGENCY = "emergency" # System compromise


@dataclass
class DaemonConfig:
    """Configuration for red team daemon."""
    mode: DaemonMode = DaemonMode.DEVELOPMENT
    attack_interval_seconds: float = 60.0      # Time between attacks
    randomize_timing: bool = True              # Add random jitter
    max_attacks_per_hour: int = 100            # Rate limiting
    escalate_attacks: bool = True              # Increase sophistication
    enable_alerts: bool = True                 # Send real-time alerts
    log_all_attempts: bool = True              # Log every attack
    production_safe: bool = True               # Extra safety checks


@dataclass
class AttackAttempt:
    """Record of single attack attempt."""
    timestamp: str
    attack_pattern: str
    category: str
    severity: str
    success: bool
    response_time_ms: float
    alert_sent: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'attack_pattern': self.attack_pattern,
            'category': self.category,
            'severity': self.severity,
            'success': self.success,
            'response_time_ms': self.response_time_ms,
            'alert_sent': self.alert_sent,
            'error_message': self.error_message
        }


@dataclass
class DaemonStatistics:
    """Statistics from daemon operation."""
    total_attacks: int = 0
    successful_attacks: int = 0
    failed_attacks: int = 0
    errors: int = 0
    alerts_sent: int = 0
    uptime_seconds: float = 0.0
    attacks_per_minute: float = 0.0
    success_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_attacks': self.total_attacks,
            'successful_attacks': self.successful_attacks,
            'failed_attacks': self.failed_attacks,
            'errors': self.errors,
            'alerts_sent': self.alerts_sent,
            'uptime_seconds': self.uptime_seconds,
            'attacks_per_minute': self.attacks_per_minute,
            'success_rate': self.success_rate
        }


class RedTeamDaemon:
    """
    Continuous red team daemon for ongoing security validation.

    Runs in background, executing randomized attacks and alerting on
    vulnerabilities in real-time.
    """

    def __init__(
        self,
        system_under_test: Any,
        config: Optional[DaemonConfig] = None,
        attack_library: Optional[AttackPatternLibrary] = None,
        alert_callback: Optional[Callable[[AttackAttempt], None]] = None,
        log_directory: Optional[str] = None
    ):
        """
        Initialize red team daemon.

        Args:
            system_under_test: System to continuously test
            config: Daemon configuration
            attack_library: Attack pattern library
            alert_callback: Function to call on successful attacks
            log_directory: Directory for logs
        """
        self.system_under_test = system_under_test
        self.config = config or DaemonConfig()
        self.attack_library = attack_library or AttackPatternLibrary()
        self.alert_callback = alert_callback
        self.log_directory = Path(log_directory or './red_team_logs')
        self.log_directory.mkdir(parents=True, exist_ok=True)

        # State
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None
        self._attack_history: List[AttackAttempt] = []
        self._statistics = DaemonStatistics()

        # Rate limiting
        self._attacks_this_hour = 0
        self._hour_start_time = time.time()

        # Attack sophistication (for escalation)
        self._sophistication_level = 1

        # Setup logging
        self._setup_logging()

    def start(self):
        """Start the red team daemon in background thread."""
        if self._running:
            self.logger.warning("Daemon already running")
            return

        self._running = True
        self._start_time = time.time()

        self._thread = threading.Thread(target=self._run_daemon, daemon=True)
        self._thread.start()

        self.logger.info(f"Red team daemon started in {self.config.mode.value} mode")

    def stop(self):
        """Stop the red team daemon."""
        if not self._running:
            return

        self._running = False

        if self._thread:
            self._thread.join(timeout=5.0)

        self.logger.info("Red team daemon stopped")

        # Save final report
        self._save_session_report()

    def is_running(self) -> bool:
        """Check if daemon is running."""
        return self._running

    def get_statistics(self) -> DaemonStatistics:
        """Get current daemon statistics."""
        # Update calculated fields
        if self._start_time:
            self._statistics.uptime_seconds = time.time() - self._start_time

            if self._statistics.uptime_seconds > 0:
                self._statistics.attacks_per_minute = (
                    self._statistics.total_attacks / (self._statistics.uptime_seconds / 60)
                )

        if self._statistics.total_attacks > 0:
            self._statistics.success_rate = (
                self._statistics.successful_attacks / self._statistics.total_attacks
            )

        return self._statistics

    def get_recent_attacks(self, count: int = 10) -> List[AttackAttempt]:
        """Get most recent attack attempts."""
        return self._attack_history[-count:]

    def force_attack(self, pattern_name: Optional[str] = None) -> AttackAttempt:
        """
        Force immediate attack execution (for testing).

        Args:
            pattern_name: Specific pattern to execute (random if None)

        Returns:
            Attack attempt result
        """
        if pattern_name:
            pattern = self.attack_library.get_pattern_by_name(pattern_name)
            if not pattern:
                raise ValueError(f"Pattern not found: {pattern_name}")
        else:
            pattern = self._select_attack_pattern()

        return self._execute_attack(pattern)

    def _run_daemon(self):
        """Main daemon loop (runs in background thread)."""
        self.logger.info("Red team daemon loop started")

        while self._running:
            try:
                # Check rate limiting
                if not self._check_rate_limit():
                    time.sleep(10)  # Wait before checking again
                    continue

                # Select attack pattern
                pattern = self._select_attack_pattern()

                # Execute attack
                attempt = self._execute_attack(pattern)

                # Handle result
                self._handle_attack_result(attempt)

                # Sleep until next attack
                sleep_time = self._calculate_sleep_time()
                time.sleep(sleep_time)

            except Exception as e:
                self.logger.error(f"Daemon error: {e}", exc_info=True)
                time.sleep(60)  # Back off on error

        self.logger.info("Red team daemon loop ended")

    def _select_attack_pattern(self) -> AttackPattern:
        """
        Select attack pattern based on configuration and sophistication.

        Returns:
            Selected attack pattern
        """
        # Filter patterns based on mode
        if self.config.mode == DaemonMode.PRODUCTION:
            # Production: only critical attacks
            candidates = self.attack_library.get_critical_patterns()
        elif self.config.mode == DaemonMode.STAGING:
            # Staging: critical and high
            candidates = self.attack_library.get_high_severity_patterns()
        else:
            # Development: all patterns
            candidates = self.attack_library.patterns

        if not candidates:
            # Fallback to all patterns
            candidates = self.attack_library.patterns

        # Apply sophistication filter (if escalation enabled)
        if self.config.escalate_attacks:
            # Higher sophistication = include more severe attacks
            if self._sophistication_level == 1:
                # Level 1: Low severity only
                candidates = [p for p in candidates if p.severity == AttackSeverity.LOW]
            elif self._sophistication_level == 2:
                # Level 2: Low and Medium
                candidates = [p for p in candidates
                            if p.severity in [AttackSeverity.LOW, AttackSeverity.MEDIUM]]
            # Level 3+: All available patterns

            if not candidates:
                # If filter excludes everything, use all
                candidates = self.attack_library.patterns

        # Random selection
        return random.choice(candidates)

    def _execute_attack(self, pattern: AttackPattern) -> AttackAttempt:
        """
        Execute attack pattern against system.

        Args:
            pattern: Attack pattern to execute

        Returns:
            Attack attempt record
        """
        start_time = time.time()

        try:
            # Production safety check
            if self.config.production_safe and self.config.mode == DaemonMode.PRODUCTION:
                # Additional validation before attacking production
                if not self._is_safe_for_production(pattern):
                    self.logger.warning(f"Skipping unsafe pattern in production: {pattern.name}")
                    return AttackAttempt(
                        timestamp=datetime.utcnow().isoformat(),
                        attack_pattern=pattern.name,
                        category=pattern.category.value,
                        severity=pattern.severity.value,
                        success=False,
                        response_time_ms=0.0,
                        error_message="Skipped: unsafe for production"
                    )

            # Execute attack
            result = pattern.execute(self.system_under_test)

            response_time = (time.time() - start_time) * 1000

            # Create attempt record
            attempt = AttackAttempt(
                timestamp=datetime.utcnow().isoformat(),
                attack_pattern=pattern.name,
                category=pattern.category.value,
                severity=pattern.severity.value,
                success=result.get('success', False),
                response_time_ms=response_time
            )

            # Update statistics
            self._statistics.total_attacks += 1
            if attempt.success:
                self._statistics.successful_attacks += 1
            else:
                self._statistics.failed_attacks += 1

            return attempt

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            self.logger.error(f"Attack execution error: {e}", exc_info=True)

            self._statistics.total_attacks += 1
            self._statistics.errors += 1

            return AttackAttempt(
                timestamp=datetime.utcnow().isoformat(),
                attack_pattern=pattern.name,
                category=pattern.category.value,
                severity=pattern.severity.value,
                success=False,
                response_time_ms=response_time,
                error_message=str(e)
            )

    def _handle_attack_result(self, attempt: AttackAttempt):
        """
        Handle attack attempt result.

        Args:
            attempt: Attack attempt to handle
        """
        # Add to history
        self._attack_history.append(attempt)

        # Limit history size
        if len(self._attack_history) > 1000:
            self._attack_history = self._attack_history[-500:]

        # Log attempt
        if self.config.log_all_attempts:
            if attempt.success:
                self.logger.warning(
                    f"SUCCESSFUL ATTACK: {attempt.attack_pattern} "
                    f"({attempt.severity}) - {attempt.response_time_ms:.1f}ms"
                )
            else:
                self.logger.debug(
                    f"Failed attack: {attempt.attack_pattern} "
                    f"({attempt.severity}) - {attempt.response_time_ms:.1f}ms"
                )

        # Send alert if needed
        if attempt.success and self.config.enable_alerts:
            self._send_alert(attempt)

        # Escalate sophistication on success
        if attempt.success and self.config.escalate_attacks:
            self._escalate_sophistication()

        # Periodic reporting
        if self._statistics.total_attacks % 100 == 0:
            self._log_statistics()

    def _send_alert(self, attempt: AttackAttempt):
        """
        Send alert for successful attack.

        Args:
            attempt: Successful attack attempt
        """
        # Determine alert level
        if attempt.severity == 'critical':
            level = AlertLevel.CRITICAL
        elif attempt.severity == 'high':
            level = AlertLevel.WARNING
        else:
            level = AlertLevel.INFO

        # Log alert
        self.logger.critical(
            f"SECURITY ALERT [{level.value.upper()}]: "
            f"System vulnerable to {attempt.attack_pattern}! "
            f"Category: {attempt.category}, Severity: {attempt.severity}"
        )

        # Call alert callback if provided
        if self.alert_callback:
            try:
                self.alert_callback(attempt)
                attempt.alert_sent = True
                self._statistics.alerts_sent += 1
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")

    def _escalate_sophistication(self):
        """Increase attack sophistication level."""
        max_level = 5
        if self._sophistication_level < max_level:
            self._sophistication_level += 1
            self.logger.info(f"Attack sophistication escalated to level {self._sophistication_level}")

    def _check_rate_limit(self) -> bool:
        """
        Check if we're within rate limits.

        Returns:
            True if attack can proceed, False if rate limited
        """
        current_time = time.time()

        # Reset hourly counter
        if current_time - self._hour_start_time >= 3600:
            self._attacks_this_hour = 0
            self._hour_start_time = current_time

        # Check limit
        if self._attacks_this_hour >= self.config.max_attacks_per_hour:
            return False

        self._attacks_this_hour += 1
        return True

    def _calculate_sleep_time(self) -> float:
        """
        Calculate time to sleep before next attack.

        Returns:
            Sleep time in seconds
        """
        base_interval = self.config.attack_interval_seconds

        if self.config.randomize_timing:
            # Add random jitter: ±30% of base interval
            jitter = base_interval * 0.3 * (2 * random.random() - 1)
            return max(1.0, base_interval + jitter)
        else:
            return base_interval

    def _is_safe_for_production(self, pattern: AttackPattern) -> bool:
        """
        Check if attack pattern is safe for production.

        Args:
            pattern: Pattern to check

        Returns:
            True if safe for production
        """
        # Only allow read-only attacks in production
        # Deny patterns that could cause data loss or corruption

        unsafe_keywords = [
            'delete', 'drop', 'truncate', 'destroy',
            'corruption', 'bomb', 'dos'
        ]

        pattern_text = (pattern.name + ' ' + pattern.description).lower()

        for keyword in unsafe_keywords:
            if keyword in pattern_text:
                return False

        return True

    def _log_statistics(self):
        """Log current statistics."""
        stats = self.get_statistics()

        self.logger.info(
            f"Daemon Statistics: "
            f"Total={stats.total_attacks}, "
            f"Success={stats.successful_attacks} ({stats.success_rate:.1%}), "
            f"Failed={stats.failed_attacks}, "
            f"Errors={stats.errors}, "
            f"Alerts={stats.alerts_sent}, "
            f"Uptime={stats.uptime_seconds:.0f}s"
        )

    def _save_session_report(self):
        """Save session report to file."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = self.log_directory / f'red_team_session_{timestamp}.json'

        report = {
            'session_start': datetime.fromtimestamp(self._start_time).isoformat() if self._start_time else None,
            'session_end': datetime.utcnow().isoformat(),
            'mode': self.config.mode.value,
            'statistics': self.get_statistics().to_dict(),
            'attack_history': [a.to_dict() for a in self._attack_history],
            'final_sophistication_level': self._sophistication_level
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Session report saved to {filename}")

    def _setup_logging(self):
        """Setup daemon logging."""
        self.logger = logging.getLogger('RedTeamDaemon')
        self.logger.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - RedTeam - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler
        log_file = self.log_directory / 'red_team_daemon.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)


# Convenience function for quick daemon startup
def start_red_team_daemon(
    system_under_test: Any,
    mode: DaemonMode = DaemonMode.DEVELOPMENT,
    alert_callback: Optional[Callable] = None
) -> RedTeamDaemon:
    """
    Start red team daemon with default configuration.

    Args:
        system_under_test: System to test
        mode: Operating mode
        alert_callback: Alert callback function

    Returns:
        Running daemon instance
    """
    config = DaemonConfig(mode=mode)
    daemon = RedTeamDaemon(
        system_under_test=system_under_test,
        config=config,
        alert_callback=alert_callback
    )
    daemon.start()
    return daemon


# Export
__all__ = [
    'RedTeamDaemon',
    'DaemonMode',
    'DaemonConfig',
    'AlertLevel',
    'AttackAttempt',
    'DaemonStatistics',
    'start_red_team_daemon'
]
