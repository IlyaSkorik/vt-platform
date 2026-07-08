import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/shared/ui";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional custom fallback renderer. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Top-level error boundary.
 *
 * Catches render-time exceptions anywhere below it and shows a recoverable
 * fallback instead of a blank screen. In production this is where crash
 * reporting (Sentry, ARCH-001 §20.1) is wired; here it logs and offers a reset.
 *
 * Note: error boundaries catch render/lifecycle errors only — async and event
 * errors are handled by TanStack Query and the API error mapper.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // Placeholder for crash reporting integration (Sentry).
    console.error("Unhandled UI error:", error, info.componentStack);
  }

  reset = (): void => {
    this.setState({ error: null });
  };

  override render(): ReactNode {
    const { error } = this.state;
    const { children, fallback } = this.props;

    if (error) {
      if (fallback) {
        return fallback(error, this.reset);
      }
      return (
        <div
          role="alert"
          className="flex min-h-svh flex-col items-center justify-center gap-4 p-6 text-center"
        >
          <div className="space-y-2">
            <h1 className="font-semibold text-2xl tracking-tight">Что-то пошло не так</h1>
            <p className="max-w-md text-muted-foreground text-sm">
              Произошла непредвиденная ошибка. Попробуйте обновить страницу или повторить попытку.
            </p>
          </div>
          <Button onClick={this.reset}>Повторить</Button>
        </div>
      );
    }

    return children;
  }
}
