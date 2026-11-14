import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

const base = "inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60";

const variants: Record<ButtonVariant, string> = {
  primary: "border border-brand bg-brand text-onBrand hover:bg-brandStrong",
  secondary: "border border-line bg-panel text-inkSoft hover:bg-hover hover:text-ink",
  danger: "border border-red-700 bg-red-700 text-white hover:bg-red-800",
  ghost: "border border-transparent px-2 text-brand hover:bg-brandSoft",
};

export function buttonClass(variant: ButtonVariant = "secondary", extra = "") {
  return `${base} ${variants[variant]} ${extra}`.trim();
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant };

/** One button style for the whole app: primary (one per screen), secondary, danger, ghost. */
export function Button({ variant = "secondary", className = "", type = "button", ...props }: ButtonProps) {
  return <button className={buttonClass(variant, className)} type={type} {...props} />;
}

export function ButtonLink({ href, variant = "secondary", className = "", children }: { href: string; variant?: ButtonVariant; className?: string; children: ReactNode }) {
  return (
    <Link className={buttonClass(variant, className)} href={href}>
      {children}
    </Link>
  );
}
