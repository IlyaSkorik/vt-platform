/**
 * TanStack Query hooks for the cabinet notification feed.
 *
 * Thin wrappers over the Orval-generated operations that unwrap the transport
 * envelope (`{ status, data: { data, meta } }`) down to the useful payload. The
 * feed is served whole — entries plus the unread count — from one request, so the
 * bell in the shell and the notifications page read the same cache entry instead
 * of polling two endpoints that could disagree.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { _Feed, _ReadReceipt } from "@/shared/api/generated/model-notifications";
import {
  listMyNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/shared/api/generated/notifications/notifications";

import { notificationKeys } from "./keys";

/** How many entries one page of the feed carries. */
const DEFAULT_LIMIT = 50;

/**
 * Unwrap the transport envelope to the inner payload.
 *
 * Generated operations are typed as a `success | problem` union, but the shared
 * mutator throws a typed `ApiError` on every non-2xx response — so a value that
 * *resolves* is always the success envelope `{ data: { data: T } }`.
 */
function unwrap<T>(response: unknown): T {
  return (response as { data: { data: T } }).data.data;
}

/** The caller's notifications, newest first, with the unread count. */
export function useNotificationFeed(limit: number = DEFAULT_LIMIT) {
  return useQuery({
    queryKey: notificationKeys.feed(limit),
    queryFn: async (): Promise<_Feed> => unwrap<_Feed>(await listMyNotifications({ limit })),
    // The shell's bell is mounted on every cabinet screen; a quiet background
    // refresh is what makes a notice arrive without the person reloading.
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  });
}

/** Mark one entry read — used when the reader opens it. */
export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notificationId: string): Promise<_ReadReceipt> =>
      unwrap<_ReadReceipt>(await markNotificationRead(notificationId)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}

/** Mark the whole feed read. */
export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<_ReadReceipt> =>
      unwrap<_ReadReceipt>(await markAllNotificationsRead()),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}
