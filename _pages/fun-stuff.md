---
layout: single
title: "Fun Stuff"
permalink: /fun-stuff/
author_profile: true
---
{% include base_path %}

<style>
  .fun-hero { display: flex; flex-wrap: wrap; gap: 1.5em; align-items: flex-start; margin: 0 0 1em; }
  .fun-hero p { margin: 0; }
  .fun-hero > p:first-child { flex: 1 1 280px; }
  .fun-hero > p:last-child { flex: 0 0 auto; }
  .fun-hero img { display: block; width: 220px; max-width: 100%; height: auto; border-radius: 8px; }
</style>
<div class="fun-hero" markdown="1">
When I'm not working or spending time with my partner and our dog, I am playing music (mainly drums but also guitar and bass), playing video games, hiking, or building random workflows or messing with technology (really, what I'd ***like*** to believe is "productive procrastination," but probably isn't ...). This page serves as a home for some of my hobbies, and I hope you enjoy a (small) window into my brain outside of work!

<img src="{{ base_path }}/images/family.jpg" alt="Evan, his partner, and their dog">
</div>

## Music

Music has always been very important to me; it was a huge part of my life growing up, from playing piano in elementary school to picking up drums in freshman year of high school. It remains a cornerstone of my day-to-day life (to my delight but, at times, other's dismay; there's music playing at all time while I work). To share this part of my life, I used the Spotify API to display my most played song over a rolling four week period, which automatically updates every Monday. Be warned; it will invariably be some kind of progressive modern metal, but sharing music is one of my favorite pasttimes. I hope you enjoy, and if you have other recommendations (based on this list or not), I'd love to hear them!! I also created lists of my top ten over the time window, and my top 25 of the year-to-date; usually something more "listenable" slips in to these lists!!

{% include spotify-top-tracks.html mode="teaser" %}

## Photo Gallery

My favorite shots from trails, cities, random adventures, and places that mean a lot to me. I don't pretend to be a photographer, but I really enjoy taking photos, and loved building a way to store/share them. This page randomly displays two, but there are many (many) more in the full gallery!!

{% include photo-gallery-teaser.html %}

[Photo Gallery →](/fun-stuff/photos/)

## Blog

I will post write-ups of the small technical and workflow projects behind that productive procrastination here soon.

[Blog →](/fun-stuff/blog/)
