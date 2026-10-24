import { Link } from "react-router-dom";

export default function AboutPage() {
  return (
    <>
      <section className="page-hero">
        <div className="container">
          <p className="eyebrow">About Us</p>
          <h1>Yale spirit, made to be worn.</h1>
          <p className="page-hero-text">
            Campus Customs is a Yale apparel shop built around one simple idea: the clothes you wear to class, to the
            game, or on the way home for break should feel like part of your Yale story.
          </p>
        </div>
      </section>

      <section className="section container about-grid">
        <div>
          <h2>Who we are</h2>
          <p>
            We started Campus Customs to make it easy to find Yale gear that actually fits the way the community lives.
            That means sweatshirts warm enough for a New Haven winter, tees for move-in day, and pieces that represent the
            residential colleges, professional schools, and teams people care about most.
          </p>
          <p>
            Every item in our shop is listed with real photos, honest descriptions, and up-to-date stock for every size,
            so you know what's available before you decide.
          </p>
        </div>
        <div>
          <h2>What we offer</h2>
          <ul className="feature-list">
            <li>
              <strong>Everyday classics</strong>: hoodies, crewnecks, and quarter-zips with bold Yale lettering.
            </li>
            <li>
              <strong>College &amp; school pride</strong>: designs for residential colleges and graduate and professional
              schools.
            </li>
            <li>
              <strong>Game-day gear</strong>: styles that celebrate Yale athletics, from football to fencing.
            </li>
            <li>
              <strong>Family favorites</strong>: Mom, Dad, Grandpa, and more, so the whole family can cheer together.
            </li>
            <li>
              <strong>Sizes XS–XXL</strong>, with stock shown size by size.
            </li>
          </ul>
        </div>
      </section>

      <section className="section section-tinted">
        <div className="container values">
          <div className="value-card">
            <p className="value-title">Community first</p>
            <p>We design for students, families, alumni, and neighbors, the people who make Yale what it is.</p>
          </div>
          <div className="value-card">
            <p className="value-title">Honest information</p>
            <p>Real product photos, clear prices, and live size availability, with no surprises at checkout.</p>
          </div>
          <div className="value-card">
            <p className="value-title">Help when you need it</p>
            <p>A shopping assistant is on the way to help you find the right style and size in seconds.</p>
          </div>
        </div>
      </section>

      <section className="section container">
        <div className="banner">
          <div>
            <h2>Ready to find your next favorite?</h2>
            <p>Browse the full Campus Customs collection.</p>
          </div>
          <Link to="/products" className="btn btn-light">
            Shop All Products
          </Link>
        </div>
      </section>
    </>
  );
}
