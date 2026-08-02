/**
 * Public API of the `auth` feature.
 *
 * The authentication capability: forms, session mutations, current-user query,
 * and the Problem-Details → form-error bridge. Pages and the app composition
 * root consume the feature only through this barrel — never its internals.
 */
export {
  authKeys,
  fetchCurrentUser,
  useForgotPassword,
  useLogin,
  useLogout,
  useRegister,
  useResendVerification,
  useResetPassword,
  useVerifyEmail,
} from "./api";
export { applyProblemToForm, formLevelMessage } from "./lib/problem-to-form";
export {
  // The platform's email and password rules themselves, not just the forms built
  // from them: the account-settings feature sets the same credentials from a
  // different screen, and two copies of "what counts as a strong password" would
  // drift the moment one of them changed.
  emailSchema,
  type ForgotPasswordValues,
  forgotPasswordSchema,
  type LoginValues,
  loginSchema,
  PASSWORD_MIN_LENGTH,
  passwordSchema,
  type RegisterValues,
  type ResetPasswordValues,
  registerSchema,
  resetPasswordSchema,
} from "./model/schemas";
export { ForgotPasswordForm } from "./ui/forgot-password-form";
export { LoginForm } from "./ui/login-form";
export { RegisterForm } from "./ui/register-form";
export { ResetPasswordForm } from "./ui/reset-password-form";
