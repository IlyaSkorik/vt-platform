import { RouterProvider } from "react-router";
import { AppProviders } from "./providers";
import { router } from "./router";

/**
 * Application root.
 *
 * Wires the provider composition root around the data router. This is the only
 * component `main.tsx` mounts.
 */
export function App(): React.JSX.Element {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
