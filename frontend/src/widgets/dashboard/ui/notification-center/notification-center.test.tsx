import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MOCK_NOTIFICATIONS } from "../../model/mock-data";
import { NotificationCenterView } from "./notification-center";

describe("NotificationCenterView", () => {
  it("shows an unread count badge derived from the items", () => {
    render(<NotificationCenterView status="success" notifications={MOCK_NOTIFICATIONS} />);
    // Three of the four fixtures are unread.
    expect(screen.getByLabelText("3 непрочитанных")).toBeInTheDocument();
  });

  it("omits the badge when everything is read", () => {
    const allRead = MOCK_NOTIFICATIONS.map((n) => ({ ...n, read: true }));
    render(<NotificationCenterView status="success" notifications={allRead} />);
    expect(screen.queryByLabelText(/непрочитанных/)).not.toBeInTheDocument();
  });

  it("renders the empty state when there are no notifications", () => {
    render(<NotificationCenterView status="empty" notifications={[]} />);
    expect(screen.getByText("Нет уведомлений")).toBeInTheDocument();
  });
});
