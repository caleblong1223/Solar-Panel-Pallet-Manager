import { forwardRef, type InputHTMLAttributes } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
};

const TextInput = forwardRef<HTMLInputElement, Props>(function TextInput({ label, ...props }, ref) {
  return (
    <label className="ui-input-label">
      <span>{label}</span>
      <input ref={ref} className="ui-input" {...props} />
    </label>
  );
});

export default TextInput;
