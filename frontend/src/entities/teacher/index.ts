export type { TeacherResource as DirectoryTeacher } from "@/shared/api/generated/model-teachers";
export { fetchTeacher, fetchTeachers, teacherDirectoryKeys, useTeachers } from "./api";
export { toCreditTeacherRequest } from "./lib";
