import { createFileRoute, Link } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: HomePage,
})

function HomePage() {
  return (
    <section className="page home">
      <p className="eyebrow">Creator dashboard</p>
      <h1>SceneWeaver</h1>
      <p className="lede">
        Story, wardrobe, generation, CSP handoff, and release preview in one local-first workspace.
      </p>
      <div className="cta-row">
        <Link to="/projects" className="btn primary">
          Open projects
        </Link>
        <Link to="/jobs" className="btn">
          Job monitor
        </Link>
      </div>
    </section>
  )
}