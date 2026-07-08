import type { Meta, StoryObj } from "@storybook/react-vite";
import { Button } from "@/shared/ui/button";
import { Toaster, toast } from "./toast";

const meta = {
  title: "Shared/UI/Toast",
  component: Toaster,
  parameters: { layout: "centered" },
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <>
        <Story />
        <Toaster />
      </>
    ),
  ],
} satisfies Meta<typeof Toaster>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: () => <Button onClick={() => toast("Уведомление отправлено")}>Показать тост</Button>,
};

export const Success: Story = {
  render: () => (
    <Button variant="success" onClick={() => toast.success("Изменения сохранены")}>
      Успех
    </Button>
  ),
};

export const ErrorToast: Story = {
  name: "Error",
  render: () => (
    <Button variant="danger" onClick={() => toast.error("Не удалось сохранить")}>
      Ошибка
    </Button>
  ),
};

export const WithDescription: Story = {
  render: () => (
    <Button
      onClick={() =>
        toast.warning("Сессия скоро истечёт", {
          description: "Сохраните изменения, чтобы не потерять данные.",
        })
      }
    >
      Предупреждение
    </Button>
  ),
};

export const WithAction: Story = {
  render: () => (
    <Button
      variant="outline"
      onClick={() =>
        toast("Участник удалён", {
          action: { label: "Отменить", onClick: () => toast.success("Восстановлено") },
        })
      }
    >
      С действием
    </Button>
  ),
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-3">
      <Button onClick={() => toast("Обычный тост")}>Message</Button>
      <Button variant="success" onClick={() => toast.success("Готово")}>
        Success
      </Button>
      <Button variant="danger" onClick={() => toast.error("Ошибка")}>
        Error
      </Button>
      <Button variant="outline" onClick={() => toast.info("Информация")}>
        Info
      </Button>
      <Button variant="outline" onClick={() => toast.warning("Внимание")}>
        Warning
      </Button>
    </div>
  ),
};
