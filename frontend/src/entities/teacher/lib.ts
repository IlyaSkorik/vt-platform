/**
 * Mapping from a Teacher Directory entry to the wizard's credit-teacher request.
 * The submission credits the teacher by `teacherDirectoryId` and stores an
 * immutable name/role snapshot; the directory stays the source of truth for
 * current data.
 */

import type { CreditTeacherRequest } from "@/shared/api/generated/model-applications";
import type { TeacherResource } from "@/shared/api/generated/model-teachers";

export function toCreditTeacherRequest(teacher: TeacherResource): CreditTeacherRequest {
  return {
    teacherDirectoryId: teacher.id,
    firstName: teacher.firstName,
    lastName: teacher.lastName,
    middleName: teacher.middleName,
    role: teacher.role,
  };
}
