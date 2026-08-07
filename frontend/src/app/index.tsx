import { RouterProvider } from "react-router";
import { AppProviders } from "./providers";
import { createAppRouter } from "./router";

/**
 * Application root.
 *
 * Wires the provider composition root around the data router. This is the only
 * component `main.tsx` mounts.
 */
// Module scope, not inside the component: the router owns navigation state, and
// rebuilding it on a re-render would drop the history the user is standing in.
const router = createAppRouter();

export function App(): React.JSX.Element {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
