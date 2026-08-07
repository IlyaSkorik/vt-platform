/**
 * Public API of the `shared/ui` segment — the VT Platform Design System.
 *
 * Every screen of the platform composes exclusively from these primitives; no
 * feature should hand-author a raw button, input, card or dialog. Components
 * are owned in-repo (Radix-backed where a headless primitive fits), accessible
 * by default (WCAG 2.1 AA), and styled only through semantic design tokens, so
 * a single theme switch (VT Light / VT Dark) restyles the whole system without
 * touching component code (ARCH-001 §8.3).
 */

export type { AlertProps } from "./alert";
export { Alert, alertVariants } from "./alert";
export type { AvatarProps, AvatarSize } from "./avatar";
export { Avatar } from "./avatar";
export type { BadgeProps } from "./badge";
export { Badge, badgeVariants } from "./badge";
export type { BrandMarkProps } from "./brand-mark";
export { BrandMark } from "./brand-mark";
export type { ButtonProps } from "./button";
export { Button, buttonVariants } from "./button";
export type { CalendarProps } from "./calendar";
export { Calendar } from "./calendar";
export type {
  CardContentProps,
  CardDescriptionProps,
  CardFooterProps,
  CardHeaderProps,
  CardProps,
  CardTitleProps,
} from "./card";
export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "./card";
export type { CheckboxProps, CheckboxSize } from "./checkbox";
export { Checkbox } from "./checkbox";
export type { ColumnDef, DataTableProps } from "./data-table";
export { DataTable } from "./data-table";
export type { DatePickerProps, DateTimePickerProps } from "./date-picker";
export { DatePicker, DateTimePicker } from "./date-picker";
export type {
  DialogContentProps,
  DialogDescriptionProps,
  DialogOverlayProps,
  DialogSectionProps,
  DialogTitleProps,
} from "./dialog";
export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
} from "./dialog";
export type { DividerOrientation, DividerProps } from "./divider";
export { Divider } from "./divider";
export type {
  DrawerContentProps,
  DrawerDescriptionProps,
  DrawerOverlayProps,
  DrawerSectionProps,
  DrawerSide,
  DrawerTitleProps,
} from "./drawer";
export {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerOverlay,
  DrawerPortal,
  DrawerTitle,
  DrawerTrigger,
} from "./drawer";
export type { EmptyStateProps } from "./empty-state";
export { EmptyState } from "./empty-state";
export type { IconButtonProps } from "./icon-button";
export { IconButton } from "./icon-button";
export type { InputProps } from "./input";
export { Input } from "./input";
export type { LoadingStateProps, LoadingStateSize } from "./loading-state";
export { LoadingState } from "./loading-state";
export type {
  EmptyPageProps,
  PageActionsProps,
  PageContainerProps,
  PageContentProps,
  PageDescriptionProps,
  PageHeaderProps,
  PageSectionProps,
  PageTitleProps,
} from "./page";
export {
  EmptyPage,
  PageActions,
  PageContainer,
  PageContent,
  PageDescription,
  PageHeader,
  PageSection,
  PageTitle,
} from "./page";
export type { PaginationItem, PaginationProps } from "./pagination";
export { getPaginationRange, Pagination } from "./pagination";
export type { PasswordInputProps } from "./password-input";
export { PasswordInput } from "./password-input";
export type { PopoverContentProps } from "./popover";
export {
  Popover,
  PopoverAnchor,
  PopoverClose,
  PopoverContent,
  PopoverTrigger,
} from "./popover";
export type { RadioGroupProps, RadioProps, RadioSize } from "./radio";
export { Radio, RadioGroup } from "./radio";
export type {
  SelectContentProps,
  SelectItemProps,
  SelectLabelProps,
  SelectOption,
  SelectOptionGroup,
  SelectProps,
  SelectSeparatorProps,
  SelectSize,
  SelectTriggerProps,
} from "./select";
export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectRoot,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "./select";
export type { SkeletonProps, SkeletonVariant } from "./skeleton";
export { Skeleton } from "./skeleton";
export type { SpinnerProps, SpinnerSize } from "./spinner";
export { Spinner } from "./spinner";
export type { SwitchProps, SwitchSize } from "./switch";
export { Switch } from "./switch";
export type { TabsContentProps, TabsListProps, TabsProps, TabsTriggerProps } from "./tabs";
export { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";
export type { TextareaProps } from "./textarea";
export { Textarea } from "./textarea";
export type { ToasterProps } from "./toast";
export { Toaster, toast } from "./toast";
export type { TooltipContentProps, TooltipProps, TooltipProviderProps } from "./tooltip";
export { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./tooltip";
