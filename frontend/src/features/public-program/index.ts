/** Public API of the `public-program` feature — reading a published programme by slug. */
export {
  fetchPublicProgram,
  type PublicProgram,
  type PublicProgramColumn,
  type PublicProgramRow,
  publicProgramKeys,
  usePublicProgram,
} from "./api";
