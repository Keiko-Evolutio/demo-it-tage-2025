import type { ReactNode } from "react";

import styles from "./AgentIcon.module.css";

export interface IAgentIconProps {
  /**
   * The name of the icon to display
   */
  iconName?: string;
  /**
   * Alt text for the icon
   * This is used for accessibility and SEO purposes
   * and should describe the icon's purpose or meaning.
   * If the icon is purely decorative, a blank string can be used.
   */
  alt: string;
  /**
   * Optional class name for the icon
   */
  iconClassName?: string;
}

export function AgentIcon({
  iconName = "Avatar_Default.svg",
  iconClassName,
  alt = "",
}: IAgentIconProps): ReactNode {
  // Check if iconName is a full URL (imported asset) or a filename
  // Imported assets from Vite will start with "/" or "data:" or "http"
  const isFullUrl = iconName?.startsWith('/') || iconName?.startsWith('data:') || iconName?.startsWith('http');
  const iconSrc = isFullUrl ? iconName : `static/assets/template-images/${iconName}`;

  return (
    <div className={styles.iconContainer}>
      <img
        alt={alt}
        className={iconClassName ?? styles.icon}
        src={iconSrc}
      />
    </div>
  );
}
