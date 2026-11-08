// Document processing status as a word plus an icon; colour only reinforces it.

import type { DocumentStatus } from "../api/types";
import { Icon, type IconName } from "./Icon";

const STATUS: Record<DocumentStatus, { label: string; icon: IconName }> = {
  pending: { label: "Pending", icon: "clock" },
  processing: { label: "Processing", icon: "spinner" },
  parsed: { label: "Parsed", icon: "check" },
  failed: { label: "Failed", icon: "alert" },
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  const { label, icon } = STATUS[status];
  return (
    <span className={`badge badge-${status}`}>
      <Icon name={icon} className={status === "processing" ? "spin" : undefined} />
      {label}
    </span>
  );
}
