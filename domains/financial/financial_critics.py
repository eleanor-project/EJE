"""
Financial Services Critics Module

Implements financial regulatory compliance critics:
- AML (Anti-Money Laundering)
- KYC (Know Your Customer)  
- Fair Lending (ECOA, FCRA)
- Fiduciary Duty
- Market Manipulation Detection
"""

from typing import Dict, Any


class AMLComplianceCritic:
    """Anti-Money Laundering compliance critic"""
    
    def __init__(self):
        self.name = "AML Compliance Critic"
        self.weight = 1.0
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        text = case.get("text", "").lower()
        amount = case.get("transaction_amount", 0)
        
        risks = []
        if any(p in text for p in ["structur", "layer", "cash", "offshore"]):
            risks.append("Suspicious transaction pattern")
        if 9000 <= amount < 10000:
            risks.append("Potential structuring below $10k threshold")
        if amount >= 50000:
            risks.append("High-value transaction requires EDD")
            
        if risks:
            return {
                "verdict": "ESCALATE" if amount < 50000 else "DENY",
                "confidence": 0.85,
                "justification": f"AML concerns: {'; '.join(risks)}",
                "metadata": {"risks": risks, "regulation": "Bank Secrecy Act"}
            }
        
        return {
            "verdict": "ALLOW",
            "confidence": 0.75,
            "justification": "No AML concerns detected",
            "metadata": {"regulation": "Bank Secrecy Act"}
        }


class KYCVerificationCritic:
    """Know Your Customer verification critic"""
    
    def __init__(self):
        self.name = "KYC Verification Critic"
        self.weight = 0.95
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        text = case.get("text", "").lower()
        verified = case.get("customer_verified", False)
        risk = case.get("risk_level", "unknown")
        
        issues = []
        if not verified:
            issues.append("Customer identity not verified")
        if risk == "high" or "high risk" in text:
            issues.append("High-risk customer requires EDD")
        if "new customer" in text and not verified:
            issues.append("New customer requires CIP")
            
        if issues:
            return {
                "verdict": "DENY",
                "confidence": 0.9,
                "justification": f"KYC requirements not met: {'; '.join(issues)}",
                "metadata": {"issues": issues, "regulation": "CIP"}
            }
            
        return {
            "verdict": "ALLOW",
            "confidence": 0.8,
            "justification": "KYC requirements satisfied",
            "metadata": {"regulation": "CIP"}
        }


class FairLendingCritic:
    """Fair lending compliance critic (ECOA, FCRA)"""
    
    def __init__(self):
        self.name = "Fair Lending Critic"
        self.weight = 1.0
        self.protected = ["race", "color", "religion", "national origin", "sex", "marital status", "age"]
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        text = case.get("text", "").lower()
        
        violations = []
        for pc in self.protected:
            if pc in text and any(w in text for w in ["deny", "decline", "reject"]):
                violations.append(f"Potential discrimination: {pc}")
                
        if ("neighborhood" in text or "zip code" in text) and "deny" in text:
            violations.append("Potential redlining")
            
        if violations:
            return {
                "verdict": "DENY",
                "confidence": 0.9,
                "justification": f"Fair lending violations: {'; '.join(violations)}",
                "metadata": {"violations": violations, "regulations": ["ECOA", "FCRA"]}
            }
            
        return {
            "verdict": "ALLOW",
            "confidence": 0.7,
            "justification": "No fair lending violations detected",
            "metadata": {"regulations": ["ECOA", "FCRA"]}
        }


class FiduciaryDutyCritic:
    """Fiduciary duty compliance critic"""
    
    def __init__(self):
        self.name = "Fiduciary Duty Critic"
        self.weight = 0.9
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        text = case.get("text", "").lower()
        
        concerns = []
        if "commission" in text and "recommend" in text:
            concerns.append("Potential conflict: commission-based recommendation")
        if "high risk" in text and ("elderly" in text or "retiree" in text):
            concerns.append("Unsuitable high-risk product for vulnerable client")
        if "recommend" in text and "fee" not in text and "cost" not in text:
            concerns.append("Inadequate fee disclosure")
            
        if concerns:
            return {
                "verdict": "ESCALATE",
                "confidence": 0.8,
                "justification": f"Fiduciary concerns: {'; '.join(concerns)}",
                "metadata": {"concerns": concerns, "standard": "Best Interest"}
            }
            
        return {
            "verdict": "ALLOW",
            "confidence": 0.75,
            "justification": "Fiduciary duty maintained",
            "metadata": {"standard": "Best Interest"}
        }


class MarketManipulationCritic:
    """Market manipulation detection critic"""
    
    def __init__(self):
        self.name = "Market Manipulation Critic"
        self.weight = 1.0
        self.patterns = ["pump", "dump", "insider", "material non-public", "wash trade", "spoofing"]
        
    def evaluate(self, case: Dict[str, Any]) -> Dict[str, Any]:
        text = case.get("text", "").lower()
        
        risks = []
        for pattern in self.patterns:
            if pattern in text:
                risks.append(f"Suspicious: {pattern}")
                
        if "coordinate" in text and "buy" in text:
            risks.append("Potential coordinated trading")
        if ("false" in text or "mislead" in text) and "statement" in text:
            risks.append("Potentially false statements")
            
        if risks:
            return {
                "verdict": "DENY",
                "confidence": 0.9,
                "justification": f"Market manipulation risks: {'; '.join(risks)}",
                "metadata": {"risks": risks, "regulations": ["Securities Exchange Act"]}
            }
            
        return {
            "verdict": "ALLOW",
            "confidence": 0.7,
            "justification": "No market manipulation detected",
            "metadata": {"regulations": ["Securities Exchange Act"]}
        }


__all__ = [
    "AMLComplianceCritic",
    "KYCVerificationCritic",
    "FairLendingCritic",
    "FiduciaryDutyCritic",
    "MarketManipulationCritic",
]
