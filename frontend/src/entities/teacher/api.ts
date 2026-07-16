/**
 * Personal Teacher Directory data access — a thin layer over the generated
 * teacher-directory client, shared by the directory page and the wizard's teacher
 * picker. Unwraps the `{ data: { data } }` envelope to plain `TeacherResource`s and
 * shares one query-key namespace so both surfaces read/invalidate the same cache.
 */

import { type UseQueryResult, useQuery } from "@tanstack/react-query";
import type { TeacherResource } from "@/shared/api/generated/model-teachers";
import {
  teachersList,
  teachersRetrieve,
} from "@/shared/api/generated/teacher-directory/teacher-directory";

export const teacherDirectoryKeys = {
  all: ["teacher-directory"] as const,
  list: (includeArchived: boolean) => ["teacher-directory", "list", includeArchived] as const,
  teacher: (teacherId: string) => ["teacher-directory", "teacher", teacherId] as const,
};

export async function fetchTeachers(includeArchived = false): Promise<TeacherResource[]> {
  const response = await teachersList({ includeArchived });
  return response.data.data;
}

export async function fetchTeacher(teacherId: string): Promise<TeacherResource> {
  const response = await teachersRetrieve(teacherId);
  if (response.status !== 200) {
    throw new Error("Failed to load teacher");
  }
  return response.data.data;
}

/** Read the current user's directory teachers (active only by default). */
export function useTeachers(includeArchived = false): UseQueryResult<TeacherResource[]> {
  return useQuery({
    queryKey: teacherDirectoryKeys.list(includeArchived),
    queryFn: () => fetchTeachers(includeArchived),
  });
}
