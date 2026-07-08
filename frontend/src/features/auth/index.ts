/**
 * Public API of the `auth` feature.
 *
 * The authentication capability: forms, session mutations, current-user query,
 * and the Problem-Details → form-error bridge. Pages and the app composition
 * root consume the feature only through this barrel — never its internals.
 */
export {
  authKeys,
  CURRENT_TERMS_VERSION,
  fetchCurrentUser,
  useForgotPassword,
  useLogin,
  useLogout,
  useRegister,
  useResetPassword,
  useVerifyEmail,
} from "./api";
export { applyProblemToForm, formLevelMessage } from "./lib/problem-to-form";
export {
  type ForgotPasswordValues,
  forgotPasswordSchema,
  type LoginValues,
  loginSchema,
  PASSWORD_MIN_LENGTH,
  type RegisterValues,
  type ResetPasswordValues,
  registerSchema,
  resetPasswordSchema,
} from "./model/schemas";
export { ForgotPasswordForm } from "./ui/forgot-password-form";
export { LoginForm } from "./ui/login-form";
export { RegisterForm } from "./ui/register-form";
export { ResetPasswordForm } from "./ui/reset-password-form";
