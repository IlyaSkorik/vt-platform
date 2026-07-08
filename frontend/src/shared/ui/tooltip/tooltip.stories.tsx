import type { Meta, StoryObj } from "@storybook/react-vite";
import { Info } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./tooltip";

const meta = {
  title: "Shared/UI/Tooltip",
  component: Tooltip,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <TooltipProvider>
        <Story />
      </TooltipProvider>
    ),
  ],
} satisfies Meta<typeof Tooltip>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant="outline">Наведите на меня</Button>
      </TooltipTrigger>
      <TooltipContent>Полезная подсказка</TooltipContent>
    </Tooltip>
  ),
};

export const IconTrigger: Story = {
  render: () => (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant="ghost" iconOnly aria-label="Подробнее">
          <Info />
        </Button>
      </TooltipTrigger>
      <TooltipContent>Дополнительная информация о поле</TooltipContent>
    </Tooltip>
  ),
};

export const Sides: Story = {
  render: () => (
    <div className="flex gap-8">
      {(["top", "right", "bottom", "left"] as const).map((side) => (
        <Tooltip key={side}>
          <TooltipTrigger asChild>
            <Button variant="outline">{side}</Button>
          </TooltipTrigger>
          <TooltipContent side={side}>Подсказка ({side})</TooltipContent>
        </Tooltip>
      ))}
    </div>
  ),
};

export const WithoutArrow: Story = {
  render: () => (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button variant="outline">Без стрелки</Button>
      </TooltipTrigger>
      <TooltipContent withArrow={false}>Подсказка без стрелки</TooltipContent>
    </Tooltip>
  ),
};
