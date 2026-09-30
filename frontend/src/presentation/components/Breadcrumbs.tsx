import { Link } from "react-router-dom";

export interface Breadcrumb {
  label: string;
  to?: string;
}

export interface BreadcrumbsProps {
  items: Breadcrumb[];
}

const itemClassName = "text-xs text-muted-foreground";
const separatorClassName = "px-1 text-xs text-muted-foreground/60";

/**
 * Renders the current position in the Party → Matter → File → Document →
 * Version hierarchy. The trailing item is the current resource and is plain
 * text; the ones before it link back up the hierarchy.
 */
export function Breadcrumbs({ items }: BreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center">
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={`${item.label}-${index}`} className="flex items-center">
            {index > 0 ? <span className={separatorClassName}>/</span> : null}
            {item.to && !isLast ? (
              <Link to={item.to} className={`${itemClassName} underline underline-offset-2`}>
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? "text-xs font-medium text-foreground" : itemClassName}>
                {item.label}
              </span>
            )}
          </span>
        );
      })}
    </nav>
  );
}
