import { Check } from 'lucide-react';
import Brand from './Brand';

export default function AuthLayout({ children }) {
  return <div className="auth-page">
    <section className="auth-story">
      <Brand />
      <div className="auth-story-copy">
        <span className="eyebrow">A BETTER VIEW OF TALENT</span>
        <h1>The right evidence.<br />A clearer shortlist.</h1>
        <p>Bring your job requirements and candidate pool together in one thoughtful workspace.</p>
        <ul>{['Compare skills and relevant experience', 'Understand the evidence behind every score', 'Keep your recruiting work in your own account'].map(text => <li key={text}><Check size={18} aria-hidden="true" />{text}</li>)}</ul>
      </div>
      <p className="auth-story-footer">Built for recruiters. Decisions stay with people.</p>
    </section>
    <section className="auth-form-panel">{children}</section>
  </div>;
}
