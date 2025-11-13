declare module '*.svg' {
  import * as React from 'react';

  // Vite default: SVG as URL string
  const content: string;
  export default content;

  // Optional: SVG as React component (use ?react suffix)
  export const ReactComponent: React.FunctionComponent<React.SVGProps<SVGSVGElement>>;
}