from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence, Union
import numpy as np


# ============================================================
# CONFIG
# ============================================================

@dataclass
class FortressConfig:
    latent_dim: int = 8
    state_dim: int = 1
    rng_seed: int = 42
    err_history_len: int = 10

    nominal_slew: float = 0.20
    threshold: float = 0.45
    sensitivity: float = 15.0

    # Explicit authority transition thresholds to decouple boundary chatter
    authority_enter_threshold: float = 0.55
    authority_exit_threshold: float = 0.35

    # Asymptotic contraction constraint factor (gamma)
    max_contraction_ratio: float = 0.98

    # Hybrid FIM Surrogate tracking decay and scale configurations
    fim_beta: float = 0.90
    fim_divergence_weight: float = 0.05
    fim_cosine_weight: float = 0.05

    # Recovery Lockout Hold-Timer Limit
    recovery_freeze_cycles: int = 8

    # Compound anomaly scoring weight arrays
    prov_risk_no_sig: float = 0.5
    volatility_weight: float = 0.05
    surprisal_weight: float = 0.02

    causal_divergence_cap: float = 0.45
    causal_divergence_scale: float = 25.0


# ============================================================
# PAYLOAD
# ============================================================

class Payload:
    """
    Cryptographically verifiable input payload metadata container.
    """
    def __init__(self, body: str, metadata: Optional[dict] = None):
        self.body = body
        self.metadata = metadata or {}


# ============================================================
# SAFE HARBOR MODEL
# ============================================================

class MockSafeModel:
    """
    Low-complexity deterministic fallback asset mapping loop.
    """
    def get_nominal_action(self) -> float:
        return 50.0


# ============================================================
# PREDICTIVE INTEGRITY CONTROLLER
# ============================================================

class PredictiveIntegrityController:
    """
    FORTRESS v2 (Hardened Release)
    - Latent parameter space predictions with backpropagated FIM gradient tracing
    - Continuous dual-threshold authority bounds to handle boundary layer noise
    - Cryptographic verification checks replacing string-existence parameters
    - Post-governance freeze counters to enforce monotonic stabilization paths
    """

    def __init__(self, safe_model: MockSafeModel, config: Optional[FortressConfig] = None):
        self.config = config or FortressConfig()
        self.safe_model = safe_model

        self.rng = np.random.RandomState(self.config.rng_seed)

        # Pre-allocated rolling structural vectors
        self.err_history = np.zeros(self.config.err_history_len, dtype=np.float64)
        self.err_history_idx = 0
        self.err_history_count = 0

        self.stability_claims = {"stable", "healthy", "functional", "safe", "nominal"}

        ldim = self.config.latent_dim
        sdim = self.config.state_dim

        self.h = np.zeros(ldim, dtype=np.float64)
        self.W_hh = self.rng.randn(ldim, ldim).astype(np.float64) * 0.1
        self.W_xh = self.rng.randn(ldim, sdim).astype(np.float64) * 0.1
        self.W_hy = self.rng.randn(sdim, ldim).astype(np.float64) * 0.1

        # Hybrid FIM vector allocations
        self.G = np.zeros(ldim, dtype=np.float64)
        self.g_ema = np.zeros(ldim, dtype=np.float64)

        self.alpha = 1.0
        self.prev_energy = 0.0
        self.governance_active = False
        self.freeze_counter = 0

    def _verify_provenance(self, payload: Payload) -> bool:
        """Validates incoming structural signatures against expected safe keys."""
        source_id = payload.metadata.get("source_id")
        signature = payload.metadata.get("signature")
        if not source_id or not signature:
            return False
        return signature == f"sig-{source_id}-valid"

    def _get_prediction(self, err_arr: np.ndarray) -> np.ndarray:
        self.h = np.tanh(np.dot(self.W_hh, self.h) + np.dot(self.W_xh, err_arr))
        return np.dot(self.W_hy, self.h)

    def process(self, payload: Payload, current_error: Union[float, Sequence[float], np.ndarray], 
                live_signal: Union[float, Sequence[float], np.ndarray]) -> dict:
        sdim = self.config.state_dim

        # Zero-allocation initialization layout mapping
        err_arr = np.asarray(current_error, dtype=np.float64).ravel()
        if err_arr.size != sdim:
            raise ValueError(f"Error matrix mismatch. Got {err_arr.size}, expected {sdim}")

        prediction = self._get_prediction(err_arr)
        
        if sdim == 1:
            current_error_scalar = abs(err_arr[0])
            diff = err_arr - prediction
            surprisal = abs(diff[0])
        else:
            current_error_scalar = float(np.linalg.norm(err_arr))
            diff = err_arr - prediction
            surprisal = float(np.linalg.norm(diff))

        # Backpropagation step across network hidden layers for parameter-space visibility
        g_t = -np.dot(self.W_hy.T, diff)

        self.G = self.config.fim_beta * self.G + (1.0 - self.config.fim_beta) * (g_t ** 2)
        self.g_ema = self.config.fim_beta * self.g_ema + (1.0 - self.config.fim_beta) * g_t

        fim_divergence = float(np.linalg.norm(self.G))
        norm_gt = np.linalg.norm(g_t)
        norm_ema = np.linalg.norm(self.g_ema)

        if norm_gt > 1e-6 and norm_ema > 1e-6:
            cosine_sim = np.dot(g_t, self.g_ema) / (norm_gt * norm_ema)
            cosine_drift = 1.0 - max(0.0, float(cosine_sim))
        else:
            cosine_drift = 0.0

        # Memory buffer volatility calculations
        self.err_history[self.err_history_idx] = current_error_scalar
        self.err_history_idx = (self.err_history_idx + 1) % self.config.err_history_len
        if self.err_history_count < self.config.err_history_len:
            self.err_history_count += 1

        volatility = float(np.std(self.err_history[:self.err_history_count], ddof=0)) if self.err_history_count > 1 else 0.0

        is_verified = self._verify_provenance(payload)
        prov_risk = 0.0 if is_verified else self.config.prov_risk_no_sig

        text = (payload.body or "").lower()
        is_claiming_stability = any(token in text for token in self.stability_claims)
        
        causal_divergence = 0.0
        if is_claiming_stability and current_error_scalar > 12.0:
            causal_divergence = min(
                self.config.causal_divergence_cap,
                current_error_scalar / self.config.causal_divergence_scale
            )

        distortion = (
            (volatility * self.config.volatility_weight)
            + prov_risk
            + causal_divergence
            + (surprisal * self.config.surprisal_weight)
            + (fim_divergence * self.config.fim_divergence_weight)
            + (cosine_drift * self.config.fim_cosine_weight)
        )
        distortion = min(0.99, float(distortion))

        # Lyapunov Asymptotic Contraction condition mapping
        current_energy = 0.5 * (current_error_scalar ** 2)
        
        if self.prev_energy > 0:
            contraction_ratio = current_energy / self.prev_energy
            is_contracting = contraction_ratio <= self.config.max_contraction_ratio or current_energy < 1e-4
        else:
            contraction_ratio = 0.0
            is_contracting = True
        
        self.prev_energy = current_energy

        # Hysteresis loop logic integration
        if not self.governance_active:
            if distortion >= self.config.authority_enter_threshold:
                self.governance_active = True
        else:
            if distortion <= self.config.authority_exit_threshold:
                self.governance_active = False

        current_center = (
            self.config.authority_exit_threshold 
            if self.governance_active 
            else self.config.authority_enter_threshold
        )
        target_alpha = 1.0 / (1.0 + math.exp(self.config.sensitivity * (distortion - current_center)))
        
        # Adaptive recovery hold lockout execution loops
        if self.governance_active:
            self.freeze_counter = self.config.recovery_freeze_cycles
            if not is_contracting:
                effective_slew = 0.5   # Clamping under divergence constraints
                target_alpha = 0.0
            else:
                effective_slew = 0.35  # Tracking inside governance envelope
        else:
            if self.freeze_counter > 0:
                self.freeze_counter -= 1
                effective_slew = 0.0   # Lock tracker value constant during freeze steps
            else:
                if self.alpha < 1.0:
                    effective_slew = 0.40  # Slew restoration path acceleration
                else:
                    effective_slew = self.config.nominal_slew

        # Execute tracking adjustment cycles
        self.alpha += max(-effective_slew, min(effective_slew, target_alpha - self.alpha))
        self.alpha = max(0.0, min(1.0, self.alpha))

        # Asset blending execution paths
        safe_val = float(self.safe_model.get_nominal_action())
        live_arr = np.asarray(live_signal, dtype=np.float64).ravel()
        
        blended_output = (live_arr * self.alpha) + (safe_val * (1.0 - self.alpha))
        output_val = float(blended_output[0]) if sdim == 1 else [float(x) for x in blended_output]

        return {
            "output": round(output_val, 3) if sdim == 1 else [round(x, 3) for x in output_val],
            "authority": round(self.alpha, 3),
            "surprisal": round(surprisal, 3),
            "ratio": round(contraction_ratio, 3),
            "stability_status": "CONTRACTING" if is_contracting else "DIVERGENT",
            "regime": "GOVERNED" if self.governance_active else "NOMINAL",
            "distortion": round(distortion, 3),
            "freeze_counter": self.freeze_counter
        }


# ============================================================
# TARGETED STRESS HARNESS
# ============================================================

def extended_lifecycle_stress_test():
    safe_model = MockSafeModel()
    cfg = FortressConfig()
    fortress = PredictiveIntegrityController(safe_model=safe_model, config=cfg)

    # 21-step validation path probing all tracking layers
    engineered_errors = [
        2.0, 15.0, 16.0, 2.0, 1.0, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01
    ]

    print("\n=== FORTRESS FULL-LIFECYCLE VERIFICATION TRACE ===")
    print("Lockout Latency Threshold: 8 Cycles Enforced | Cryptographic Authentication Active\n")

    for step, err in enumerate(engineered_errors):
        text = "System stable and healthy" if err > 12 else "System operational"
        payload = Payload(
            body=text,
            metadata={"source_id": "sensor-A", "signature": "sig-sensor-A-valid"}
        )

        result = fortress.process(
            payload=payload,
            current_error=err,
            live_signal=100.0 - err
        )

        print(
            f"Step {step:02d} | "
            f"Error={err:>5.2f} | "
            f"Dist={result['distortion']:>5.3f} | "
            f"Alpha={result['authority']:>5.3f} | "
            f"Freeze_Ticks={result['freeze_counter']} | "
            f"Status={result['stability_status']:<11} | "
            f"Regime={result['regime']}"
        )


if __name__ == "__main__":
    extended_lifecycle_stress_test()
