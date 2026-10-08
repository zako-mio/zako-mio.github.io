export interface ContactProps {
  email: string;
  github: string;
}

export function Contact({ email, github }: ContactProps) {
  return (
    <section id="contact" className="section section--tight">
      <div className="container">
        <header className="section__head">
          <h2 className="section__title">联系</h2>
          <p className="section__subtitle">欢迎交流技术方向、开源协作或数据科学问题</p>
        </header>

        <ul className="contact__list">
          <li>
            <a className="contact__link" href={`mailto:${email}`}>
              <span className="contact__k">邮箱</span>
              <span className="contact__v">{email}</span>
            </a>
          </li>
          <li>
            <a className="contact__link" href={github} rel="noopener noreferrer" target="_blank">
              <span className="contact__k">GitHub</span>
              <span className="contact__v">{github.replace(/^https?:\/\//, '')}</span>
            </a>
          </li>
        </ul>
      </div>
    </section>
  );
}
