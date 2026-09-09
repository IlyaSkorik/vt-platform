import type { Meta, StoryObj } from "@storybook/react-vite";
import { PasswordRequirements } from "./password-requirements";

const meta = {
  title: "Features/Auth/PasswordRequirements",
  component: PasswordRequirements,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  args: { value: "" },
  decorators: [
    (Story) => (
      <div className="w-80">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof PasswordRequirements>;

export default meta;

type Story = StoryObj<typeof meta>;

/** An untouched field: the whole policy stated up front, nothing yet marked wrong. */
export const Empty: Story = {};

/** Mid-typing — long enough and mixed case, still missing a digit and a symbol. */
export const PartiallyMet: Story = { args: { value: "StrongPass" } };

export const AllMet: Story = { args: { value: "StrongPass123!" } };

/** After a rejected submit: the rules still unmet are the reason it was rejected. */
export const Rejected: Story = { args: { value: "StrongPass", invalid: true } };
