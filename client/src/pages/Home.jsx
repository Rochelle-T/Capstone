import React, { useContext, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import '../styles/Home.css';

const techniques = [
  {
    number: '01',
    title: 'Transit photometry',
    description: 'Measure the tiny, periodic dip in a star’s brightness when a planet crosses its face.',
  },
  {
    number: '02',
    title: 'Radial velocity',
    description: 'Detect the subtle gravitational wobble a planet induces in its host star.',
  },
  {
    number: '03',
    title: 'Direct imaging',
    description: 'Separate faint planetary light from the glare of the star it orbits.',
  },
];

export default function Home() {
  const { user } = useContext(AuthContext);
  const [scrollProgress, setScrollProgress] = useState(0);
  const pathPoint = (progress) => {
    const inverse = 1 - progress;
    return {
      x: (inverse ** 3 * 86) + (3 * inverse ** 2 * progress * 72)
        + (3 * inverse * progress ** 2 * 31) + (progress ** 3 * 14),
      y: (inverse ** 3 * 12) + (3 * inverse ** 2 * progress * 23)
        + (3 * inverse * progress ** 2 * 71) + (progress ** 3 * 88),
    };
  };

  useEffect(() => {
    const updateOrbit = () => {
      const scrollableHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = scrollableHeight > 0
        ? Math.min(window.scrollY / scrollableHeight, 1)
        : 0;
      setScrollProgress(progress);
    };

    window.addEventListener('scroll', updateOrbit, { passive: true });
    window.addEventListener('resize', updateOrbit);
    updateOrbit();
    return () => {
      window.removeEventListener('scroll', updateOrbit);
      window.removeEventListener('resize', updateOrbit);
    };
  }, []);
  const planetPosition = pathPoint(scrollProgress);

  return (
    <div className="home-page">
      <header className="home-nav">
        <Link to="/" className="home-brand"><span>AS</span> AstroSense</Link>
        <nav>
          <a href="#exoplanets">Exoplanets</a>
          <a href="#techniques">Techniques</a>
          <Link to={user ? '/dashboard' : '/login'} className="home-nav-button">
            {user ? 'Mission Control' : 'Open Mission Control'}
          </Link>
        </nav>
      </header>

      <svg className="page-orbit-path" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <path d="M 86 12 C 72 23, 31 71, 14 88" />
      </svg>
      <div
        className="page-planet"
        style={{ left: `${planetPosition.x}%`, top: `${planetPosition.y}%` }}
        aria-hidden="true"
      ></div>

      <main>
        <section className="home-hero">
          <div className="hero-copy">
            <span className="eyebrow">ASTRONOMICAL DATA INTELLIGENCE</span>
            <h1>Read the signals of distant worlds.</h1>
            <p>
              AstroSense turns stellar observations into clear, evidence-led
              exoplanet analysis.
            </p>
            <div className="hero-actions">
              <Link to={user ? '/dashboard' : '/register'} className="home-primary-button">
                {user ? 'Open workspace' : 'Start exploring'}
              </Link>
              <a href="#exoplanets" className="home-secondary-button">Learn the science</a>
            </div>
          </div>
          <div className="orbit-stage" aria-label="An exoplanet crossing the field of view">
            <span className="orbit-label">TRANSIT OBSERVATION / FIELD OF VIEW</span>
          </div>
        </section>

        <section id="exoplanets" className="home-section definition-section">
          <div className="section-intro">
            <span className="eyebrow">THE SCIENCE</span>
            <h2>What is an exoplanet?</h2>
          </div>
          <div className="definition-copy">
            <p>
              An exoplanet is a planet beyond our solar system. Most are too
              distant and faint to see directly, so scientists study the
              measurable effects they have on their host stars.
            </p>
            <p>
              Each observation is a signal: a change in brightness, a shift in
              spectrum, or a trace of heat. AstroSense helps organize those
              signals into a repeatable discovery workflow.
            </p>
          </div>
        </section>

        <section id="techniques" className="home-section">
          <div className="section-intro">
            <span className="eyebrow">DISCOVERY METHODS</span>
            <h2>How do we find them?</h2>
          </div>
          <div className="technique-grid">
            {techniques.map((technique) => (
              <article className="technique-card" key={technique.number}>
                <span className="technique-number">{technique.number}</span>
                <h3>{technique.title}</h3>
                <p>{technique.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="home-cta">
          <div>
            <span className="eyebrow">YOUR OBSERVATORY WORKSPACE</span>
            <h2>Move from raw FITS files to scientific insight.</h2>
          </div>
          <Link to={user ? '/dashboard' : '/login'} className="home-primary-button">
            {user ? 'Return to workspace' : 'Enter Mission Control'}
          </Link>
        </section>
      </main>
    </div>
  );
}
