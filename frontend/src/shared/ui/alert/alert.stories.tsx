import type { Meta, StoryObj } from "@storybook/react-vite";
import { Alert } from "./alert";

const meta = {
  title: "Shared/UI/Alert",
  component: Alert,
  parameters: { layout: "padded" },
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["info", "success", "warning", "danger"],
    },
    dismissible: { control: "boolean" },
  },
  args: {
    variant: "info",
    title: "Информация",
    children: "Это информационное сообщение для пользователя.",
  },
} satisfies Meta<typeof Alert>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Info: Story = {};

export const Success: Story = {
  args: { variant: "success", title: "Успешно", children: "Изменения сохранены." },
};

export const Warning: Story = {
  args: {
    variant: "warning",
    title: "Предупреждение",
    children: "Срок действия скоро истечёт.",
  },
};

export const Danger: Story = {
  args: {
    variant: "danger",
    title: "Ошибка",
    children: "Не удалось загрузить данные. Повторите попытку.",
  },
};

export const Dismissible: Story = {
  args: {
    variant: "info",
    title: "Уведомление",
    children: "Это уведомление можно закрыть.",
    dismissible: true,
  },
};

export const TitleOnly: Story = {
  args: { variant: "success", title: "Профиль обновлён", children: undefined },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-col gap-3">
      <Alert variant="info" title="Информация">
        Информационное сообщение.
      </Alert>
      <Alert variant="success" title="Успешно">
        Операция выполнена.
      </Alert>
      <Alert variant="warning" title="Предупреждение">
        Обратите внимание на это.
      </Alert>
      <Alert variant="danger" title="Ошибка">
        Что-то пошло не так.
      </Alert>
    </div>
  ),
  args: { title: undefined, children: undefined },
};
