/** Public API of the `shared/config` segment. */

export { APP_NAME, APP_NAME_EN, SUPPORT_EMAIL } from "./app";
export { type Env, env } from "./env";
export {
  getNavigation,
  NAV_ICONS,
  NAVIGATION,
  type NavCrumb,
  type NavGroup,
  type NavItem,
  type NavModel,
  resolveBreadcrumbs,
} from "./navigation";
export { ROUTES, type RoutePath } from "./routes";
