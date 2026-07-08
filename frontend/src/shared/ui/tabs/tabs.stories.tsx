import type { Meta, StoryObj } from "@storybook/react-vite";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";

const meta = {
  title: "Shared/UI/Tabs",
  component: Tabs,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
} satisfies Meta<typeof Tabs>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => (
    <Tabs defaultValue="account" className="w-96">
      <TabsList>
        <TabsTrigger value="account">Аккаунт</TabsTrigger>
        <TabsTrigger value="password">Пароль</TabsTrigger>
        <TabsTrigger value="team">Команда</TabsTrigger>
      </TabsList>
      <TabsContent value="account" className="p-4 text-sm text-foreground">
        Настройки аккаунта участника.
      </TabsContent>
      <TabsContent value="password" className="p-4 text-sm text-foreground">
        Смена пароля и безопасность.
      </TabsContent>
      <TabsContent value="team" className="p-4 text-sm text-foreground">
        Управление участниками команды.
      </TabsContent>
    </Tabs>
  ),
};

export const WithDisabled: Story = {
  render: () => (
    <Tabs defaultValue="overview" className="w-96">
      <TabsList>
        <TabsTrigger value="overview">Обзор</TabsTrigger>
        <TabsTrigger value="stats">Статистика</TabsTrigger>
        <TabsTrigger value="billing" disabled>
          Оплата
        </TabsTrigger>
      </TabsList>
      <TabsContent value="overview" className="p-4 text-sm text-foreground">
        Общая информация.
      </TabsContent>
      <TabsContent value="stats" className="p-4 text-sm text-foreground">
        Показатели и метрики.
      </TabsContent>
    </Tabs>
  ),
};

export const Vertical: Story = {
  render: () => (
    <Tabs defaultValue="one" orientation="vertical" className="flex-row gap-4">
      <TabsList>
        <TabsTrigger value="one">Первая</TabsTrigger>
        <TabsTrigger value="two">Вторая</TabsTrigger>
        <TabsTrigger value="three">Третья</TabsTrigger>
      </TabsList>
      <TabsContent value="one" className="text-sm text-foreground">
        Содержимое первой вкладки.
      </TabsContent>
      <TabsContent value="two" className="text-sm text-foreground">
        Содержимое второй вкладки.
      </TabsContent>
      <TabsContent value="three" className="text-sm text-foreground">
        Содержимое третьей вкладки.
      </TabsContent>
    </Tabs>
  ),
};
