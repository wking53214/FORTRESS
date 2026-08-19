"""
PredictiveStateController

Calculates variance, energy delta, and overrides blending coefficients for states with transition logging.

Source: [source: 1]
Extracted verbatim from artifact_8.json (code_modules[].body) - not repaired.
"""

class PredictiveStateController:
 def init(
 self,
 fallback_provider: BackupActionProvider,
 config: Optional[ProcessingPipelineConfig] = None,
 ):
 self.config = config or ProcessingPipelineConfig()
 self.fallback_provider = fallback_provider

 self.random_generator = np.random.RandomState(self.config.random_seed)
 self.error_history: deque[float] = deque(maxlen=self.config.history_buffer_limit)

 self.target_status_tokens = {"stable", "healthy", "functional", "safe", "nominal"}

 latent_dim = self.config.latent_dimension
 state_dim = self.config.state_dimension

 self.latent_state_vector = np.zeros(latent_dim)
 self.weight_matrix_recurrent = self.random_generator.randn(latent_dim, latent_dim) * 0.1
 self.weight_matrix_input = self.random_generator.randn(latent_dim, state_dim) * 0.1
 self.weight_matrix_output = self.random_generator.randn(state_dim, latent_dim) * 0.1

 self.blending_coefficient: float = 1.0
 self.prior_step_energy: float = 0.0
 self.is_state_override_engaged: bool = False
 
 # NEW: Transition logging
 self.state_transitions: List[FortressStateTransition] = []

 def _compute_latent_projection(self, observation: np.ndarray) -> np.ndarray:
 flat_observation = np.asarray(observation).reshape(-1)
 expected_dimension = self.weight_matrix_input.shape[1]

 if flat_observation.shape[0] != expected_dimension:
 raise ValueError(
 f"Dimension mismatch: input shape {flat_observation.shape[0]} "
 f"does not match expected {expected_dimension}."
 )

 self.latent_state_vector = np.tanh(
 np.dot(self.weight_matrix_recurrent, self.latent_state_vector)
 + np.dot(self.weight_matrix_input, flat_observation)
 )

 return np.dot(self.weight_matrix_output, self.latent_state_vector).reshape(-1)

 def _calculate_target_coefficient(self, variance: float) -> float:
 return 1.0 / (
 1.0 + math.exp(self.config.sigmoid_sensitivity * (variance - self.config.activation_threshold))
 )

 def _evaluate_composite_variance(
 self,
 payload: InputPayload,
 scalar_error: float,
 prediction_error: float,
 ) -> float:
 self.error_history.append(scalar_error)
 calculated_variance = (
 float(np.std(np.asarray(self.error_history), ddof=0))
 if len(self.error_history) > 1
 else 0.0
 )

 has_valid_signatures = "source_id" in payload.metadata and "signature" in payload.metadata
 verification_penalty = 0.0 if has_valid_signatures else self.config.unverified_source_penalty

 normalized_text = (payload.content_body or "").lower()
 contains_target_tokens = any(token in normalized_text for token in self.target_status_tokens)

 divergence_metric = 0.0
 if contains_target_tokens and scalar_error > 12.0:
 divergence_metric = min(
 self.config.divergence_saturation_cap,
 (scalar_error / self.config.divergence_scaling_factor),
 )

 composite_variance = (
 (calculated_variance * self.config.history_variance_weight)
 + verification_penalty
 + divergence_metric
 + (prediction_error * self.config.prediction_error_weight)
 )

 return min(0.99, float(composite_variance))

 def process_step(
 self,
 payload: InputPayload,
 current_error_input: Union[float, Sequence[float], np.ndarray],
 live_signal_input: Union[float, Sequence[float]],
 ) -> Dict[str, Any]:
 state_dim = self.config.state_dimension

 error_array = np.asarray(current_error_input).reshape(-1)
 if error_array.size == 0:
 raise ValueError("Error tracking array input cannot be empty.")

 if error_array.size != state_dim and not (state_dim == 1 and error_array.size == 1):
 raise ValueError(
 f"Dimension mismatch: input size {error_array.size} must match target {state_dim}."
 )

 projected_state = self._compute_latent_projection(error_array)

 if projected_state.size == 1:
 prediction_error = float(abs(error_array.item() - projected_state[0]))
 scalar_error = float(error_array.item())
 else:
 state_delta = error_array - projected_state
 prediction_error = float(np.linalg.norm(state_delta))
 scalar_error = float(np.linalg.norm(error_array))

 composite_variance = self._evaluate_composite_variance(payload, scalar_error, prediction_error)

 step_energy = 0.5 * (scalar_error 2)
 energy_rate_of_change = step_energy - self.prior_step_energy
 self.prior_step_energy = step_energy

 target_coefficient = self._calculate_target_coefficient(composite_variance)
 active_adjustment_rate = self.config.nominal_adjustment_rate

 previous_override_state = self.is_state_override_engaged

 if not self.is_state_override_engaged:
 if composite_variance >= self.config.state_engagement_threshold:
 self.is_state_override_engaged = True
 # Log transition
 self.state_transitions.append(
 FortressStateTransition(
 timestamp=dt.utcnow(),
 previous_mode="NOMINAL",
 new_mode="OVERRIDE",
 trigger_variance=composite_variance,
 trigger_energy_delta=energy_rate_of_change,
 reason=f"Variance {composite_variance:.3f} exceeded engagement threshold {self.config.state_engagement_threshold}",
 )
 )
 logger.warning(f"FORTRESS state transition: NOMINAL -> OVERRIDE (variance={composite_variance:.3f})")
 else:
 if composite_variance <= self.config.state_disengagement_threshold:
 self.is_state_override_engaged = False
 # Log transition
 self.state_transitions.append(
 FortressStateTransition(
 timestamp=dt.utcnow(),
 previous_mode="OVERRIDE",
 new_mode="NOMINAL",
 trigger_variance=composite_variance,
 trigger_energy_delta=energy_rate_of_change,
 reason=f"Variance {composite_variance:.3f} fell below disengagement threshold {self.config.state_disengagement_threshold}",
 )
 )
 logger.info(f"FORTRESS state transition: OVERRIDE -> NOMINAL (variance={composite_variance:.3f})")

 if energy_rate_of_change > 0 and self.is_state_override_engaged:
 active_adjustment_rate = 0.5
 target_coefficient = 0.0

 coefficient_delta = target_coefficient - self.blending_coefficient
 clamped_step = max(-active_adjustment_rate, min(active_adjustment_rate, coefficient_delta))

 self.blending_coefficient += clamped_step
 self.blending_coefficient = max(0.0, min(1.0, self.blending_coefficient))

 fallback_value = float(self.fallback_provider.get_default_action())
 live_signal_array = np.asarray(live_signal_input).reshape(-1)

 if live_signal_array.size == 1:
 blended_value = (live_signal_array.item() * self.blending_coefficient) + (
 fallback_value * (1.0 - self.blending_coefficient)
 )
 final_output_value = float(blended_value)
 else:
 if live_signal_array.size != state_dim:
 raise ValueError("Live signal input dimensions do not match system dimensions.")

 blended_vectors = (live_signal_array * self.blending_coefficient) + (
 fallback_value * (1.0 - self.blending_coefficient)
 )
 final_output_value = [float(element) for element in blended_vectors]

 return {
 "computed_output": (
 round(final_output_value, 3)
 if isinstance(final_output_value, float)
 else [round(val, 3) for val in final_output_value]
 ),
 "blending_coefficient": round(self.blending_coefficient, 3),
 "prediction_error": round(prediction_error, 3),
 "energy_state_trend": "STABLE" if energy_rate_of_change <= 0 else "DIVERGENT",
 "operational_mode": "OVERRIDE" if self.is_state_override_engaged else "NOMINAL",
 "evaluated_variance": round(composite_variance, 3),
 "mode_changed": previous_override_state != self.is_state_override_engaged,
 }
