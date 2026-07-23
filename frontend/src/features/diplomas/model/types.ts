import type {
  AssignmentResponse,
  CreateAssignmentRequest,
  CreateTemplateRequest,
  TemplateResponse,
} from "@/shared/api/generated/model-diplomas";
import type { TemplateField } from "./constructor";

/** A diploma template in the reusable library. */
export type DiplomaTemplate = TemplateResponse;

/** A binding of a template to a (competition, nomination) pair. */
export type DiplomaAssignment = AssignmentResponse;

/** Payload for creating an assignment. */
export type CreateAssignmentPayload = CreateAssignmentRequest;

/** Payload for creating a template. */
export type CreateTemplatePayload = CreateTemplateRequest;

/** A template's saved layout: its placed fields plus the layout revision. */
export interface TemplateLayout {
  fields: TemplateField[];
  revision: number;
}
