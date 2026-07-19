/**
 * Public API of the `organization` feature — the staff-facing organization
 * profile: reading it, editing it, and the form model that backs the edit UI.
 */
export {
  fetchOrganizationProfile,
  type OrganizationProfile,
  type OrganizationProfileUpdate,
  organizationProfileKeys,
  updateOrganizationProfile,
  useOrganizationProfileQuery,
  useUpdateOrganizationProfileMutation,
} from "./api/profile";
export {
  formValuesToUpdate,
  ORGANIZATION_PROFILE_FIELDS,
  type OrganizationProfileFormValues,
  organizationProfileSchema,
  profileToFormValues,
} from "./model/profile-form";
