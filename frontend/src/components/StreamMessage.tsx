import { useEffect, useState } from 'react';

interface StreamMessageProps {
  message: string;
  onComplete: () => void;
}

export const StreamMessage = ({ message, onComplete }: StreamMessageProps) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onComplete, 300); // Allow time for fade out animation
    }, 2000); // Show message for 2 seconds

    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <div
      className={`transition-all duration-300 ${
        visible ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform translate-y-2'
      }`}
    >
      <div className="bg-white/90 backdrop-blur-sm rounded-xl p-4 shadow-lg border border-white/20">
        <p className="text-slate-700">{message}</p>
      </div>
    </div>
  );
}; 