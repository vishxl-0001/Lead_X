import React, { useState } from 'react';
import { X, MessageSquare, Save, Sparkles, Check } from 'lucide-react';

interface TemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTemplate: string;
  onSaveTemplate: (newTemplate: string) => void;
}

export const TemplateModal: React.FC<TemplateModalProps> = ({
  isOpen,
  onClose,
  currentTemplate,
  onSaveTemplate,
}) => {
  if (!isOpen) return null;

  const [template, setTemplate] = useState(currentTemplate);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = () => {
    onSaveTemplate(template);
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 800);
  };

  const previewMessage = template
    .replace('{business_name}', 'Sharma Electricals')
    .replace('{area}', 'Indiranagar')
    .replace('{category}', 'Electrician')
    .replace('{owner_name}', 'Mr. Sharma');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-dark-800 border border-dark-700 w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-dark-700 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Customize WhatsApp Outreach Pitch</h3>
              <p className="text-xs text-slate-400">
                This message auto-populates when clicking &quot;Chat on WhatsApp&quot;.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-dark-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 text-xs text-slate-300">
          <div>
            <label className="block text-slate-300 font-semibold mb-1.5">
              Pitch Template Text
            </label>
            <textarea
              rows={4}
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              className="w-full p-3 rounded-xl bg-dark-900 border border-dark-600 text-white outline-none focus:border-emerald-500 font-mono text-xs leading-relaxed resize-none"
            />
          </div>

          {/* Dynamic Tags Available */}
          <div className="bg-dark-900 p-3 rounded-xl border border-dark-700">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" /> Dynamic Interpolation Tags
            </p>
            <div className="flex flex-wrap gap-1.5 text-[11px]">
              {['{business_name}', '{area}', '{category}', '{owner_name}'].map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => setTemplate((prev) => `${prev} ${tag}`)}
                  className="px-2 py-0.5 rounded-md bg-dark-700 hover:bg-dark-600 text-emerald-300 font-mono border border-emerald-500/30 transition-colors"
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Live Preview */}
          <div className="bg-emerald-950/20 p-3.5 rounded-xl border border-emerald-500/20">
            <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-400 block mb-1">
              WhatsApp Chat Preview (What they see):
            </span>
            <div className="bg-dark-900/90 p-3 rounded-lg border border-dark-700 text-slate-200 text-xs italic leading-relaxed">
              &ldquo;{previewMessage}&rdquo;
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-700 bg-dark-800/90 flex items-center justify-end space-x-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-dark-700 hover:bg-dark-600 text-slate-300 font-medium text-xs transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/30 transition-all"
          >
            {savedSuccess ? (
              <>
                <Check className="w-4 h-4 text-white" />
                <span>Saved!</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>Save Template</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
