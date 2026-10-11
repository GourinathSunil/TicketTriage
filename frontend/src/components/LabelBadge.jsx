import React from 'react';

export default function LabelBadge({ labelId, labels = [], showRemove = false, onRemove = null }) {
  const lblConfig = labels.find((l) => l.id === labelId);
  const displayName = lblConfig?.name || labelId;
  const hexColor = lblConfig?.color || '#6366F1';

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors"
      style={{
        backgroundColor: `${hexColor}18`,
        color: hexColor,
        borderColor: `${hexColor}40`,
      }}
      title={lblConfig?.description || displayName}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: hexColor }}
      ></span>
      <span>{displayName}</span>
      {showRemove && onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove(labelId);
          }}
          className="ml-1 hover:text-white transition-colors"
        >
          &times;
        </button>
      )}
    </span>
  );
}
