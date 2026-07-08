import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "@/shared/ui/button";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "./drawer";
import type { DrawerSide } from "./types";

const meta = {
  title: "Shared/UI/Drawer",
  component: Drawer,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
} satisfies Meta<typeof Drawer>;

export default meta;

type Story = StoryObj<typeof meta>;

function DrawerDemo({ side }: { side: DrawerSide }) {
  return (
    <Drawer>
      <DrawerTrigger asChild>
        <Button variant="outline">Открыть ({side})</Button>
      </DrawerTrigger>
      <DrawerContent side={side}>
        <DrawerHeader>
          <DrawerTitle>Фильтры</DrawerTitle>
          <DrawerDescription>Настройте параметры отображения списка.</DrawerDescription>
        </DrawerHeader>
        <DrawerFooter>
          <DrawerClose asChild>
            <Button variant="outline">Отмена</Button>
          </DrawerClose>
          <DrawerClose asChild>
            <Button>Применить</Button>
          </DrawerClose>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}

export const Right: Story = { render: () => <DrawerDemo side="right" /> };
export const Left: Story = { render: () => <DrawerDemo side="left" /> };
export const Top: Story = { render: () => <DrawerDemo side="top" /> };
export const Bottom: Story = { render: () => <DrawerDemo side="bottom" /> };

export const AllSides: Story = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <DrawerDemo side="left" />
      <DrawerDemo side="right" />
      <DrawerDemo side="top" />
      <DrawerDemo side="bottom" />
    </div>
  ),
};
