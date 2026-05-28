import { cn } from "@/lib/utils";

const maxWidthClasses = {
  lg: "max-w-lg",
  xl: "max-w-xl",
  "4xl": "max-w-4xl",
  "6xl": "max-w-6xl",
  full: "max-w-none",
} as const;

export type DashboardPageMaxWidth = keyof typeof maxWidthClasses;

interface DashboardPageContainerProps {
  children: React.ReactNode;
  maxWidth?: DashboardPageMaxWidth;
  className?: string;
}

export function DashboardPageContainer({
  children,
  maxWidth = "6xl",
  className,
}: DashboardPageContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto flex w-full flex-1 flex-col px-4 py-6 sm:px-6",
        maxWidthClasses[maxWidth],
        className
      )}
    >
      {children}
    </div>
  );
}
