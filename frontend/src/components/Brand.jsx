import { Link } from 'react-router-dom';
import { ScanLine } from 'lucide-react';

export default function Brand() {
  return <Link to="/" className="brand" aria-label="HireLens AI home">
    <span className="brand-icon"><ScanLine aria-hidden="true" /></span>
    <span>HireLens<span className="brand-ai"> AI</span><small>RECRUITING INTELLIGENCE</small></span>
  </Link>;
}
