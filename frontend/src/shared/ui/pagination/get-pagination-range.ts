import type { PaginationItem } from "./types";

/**
 * Build the list of page tokens to render, inserting `"ellipsis"` markers for
 * truncated gaps. Always shows the first and last page plus `siblingCount`
 * pages around the current one. Pure and index-safe.
 */
export function getPaginationRange(
  page: number,
  pageCount: number,
  siblingCount = 1,
): PaginationItem[] {
  if (pageCount <= 0) {
    return [];
  }

  // First page, last page, current + siblings, and two ellipses.
  const totalVisible = siblingCount * 2 + 5;

  if (pageCount <= totalVisible) {
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  }

  const leftSibling = Math.max(page - siblingCount, 1);
  const rightSibling = Math.min(page + siblingCount, pageCount);

  const showLeftEllipsis = leftSibling > 2;
  const showRightEllipsis = rightSibling < pageCount - 1;

  const items: PaginationItem[] = [];

  if (!showLeftEllipsis && showRightEllipsis) {
    const leftCount = siblingCount * 2 + 3;
    for (let index = 1; index <= leftCount; index += 1) {
      items.push(index);
    }
    items.push("ellipsis", pageCount);
    return items;
  }

  if (showLeftEllipsis && !showRightEllipsis) {
    const rightCount = siblingCount * 2 + 3;
    items.push(1, "ellipsis");
    for (let index = pageCount - rightCount + 1; index <= pageCount; index += 1) {
      items.push(index);
    }
    return items;
  }

  items.push(1, "ellipsis");
  for (let index = leftSibling; index <= rightSibling; index += 1) {
    items.push(index);
  }
  items.push("ellipsis", pageCount);
  return items;
}
