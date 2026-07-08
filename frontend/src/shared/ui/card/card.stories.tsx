import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "../button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./card";

const meta = {
  title: "Shared/UI/Card",
  component: Card,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
} satisfies Meta<typeof Card>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Card className="w-80">
      <CardHeader>
        <CardTitle>Профиль участника</CardTitle>
        <CardDescription>Основные сведения об участнике программы.</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-foreground">
          Здесь размещается основное содержимое карточки: текст, поля или медиа.
        </p>
      </CardContent>
      <CardFooter className="justify-end gap-2">
        <Button variant="ghost">Отмена</Button>
        <Button>Сохранить</Button>
      </CardFooter>
    </Card>
  ),
};

export const HeaderOnly: Story = {
  render: () => (
    <Card className="w-80">
      <CardHeader>
        <CardTitle>Только заголовок</CardTitle>
        <CardDescription>Карточка без тела и подвала.</CardDescription>
      </CardHeader>
    </Card>
  ),
};

export const ContentOnly: Story = {
  render: () => (
    <Card className="w-80">
      <CardContent className="pt-6">
        <p className="text-sm text-foreground">Карточка только с содержимым.</p>
      </CardContent>
    </Card>
  ),
};
