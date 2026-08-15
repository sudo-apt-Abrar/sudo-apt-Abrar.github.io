// Pulls recent Strava activity + stats and writes data/strava.json.
// Requires env vars: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN
// Run via the "fetch-strava" GitHub Action (see .github/workflows/fetch-strava.yml).

const { STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_REFRESH_TOKEN } = process.env;

if (!STRAVA_CLIENT_ID || !STRAVA_CLIENT_SECRET || !STRAVA_REFRESH_TOKEN) {
  console.error("Missing STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET / STRAVA_REFRESH_TOKEN env vars.");
  process.exit(1);
}

async function getAccessToken() {
  const res = await fetch("https://www.strava.com/oauth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      client_id: STRAVA_CLIENT_ID,
      client_secret: STRAVA_CLIENT_SECRET,
      refresh_token: STRAVA_REFRESH_TOKEN,
      grant_type: "refresh_token",
    }),
  });
  if (!res.ok) throw new Error(`token refresh failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  return data.access_token;
}

async function stravaGet(path, token) {
  const res = await fetch(`https://www.strava.com/api/v3${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status} ${await res.text()}`);
  return res.json();
}

function startOfWeek(d) {
  const date = new Date(d);
  const day = (date.getUTCDay() + 6) % 7; // Monday = 0
  date.setUTCDate(date.getUTCDate() - day);
  date.setUTCHours(0, 0, 0, 0);
  return date;
}

function summarizeActivity(a) {
  return {
    id: a.id,
    name: a.name,
    type: a.type,
    date: a.start_date_local,
    distance_m: a.distance,
    moving_time_s: a.moving_time,
    elevation_m: a.total_elevation_gain,
    avg_speed_mps: a.average_speed,
  };
}

function buildWeeklyVolume(activities, weeks = 10) {
  const buckets = new Map();
  const now = new Date();
  for (let i = 0; i < weeks; i++) {
    const wk = new Date(now);
    wk.setUTCDate(wk.getUTCDate() - i * 7);
    const key = startOfWeek(wk).toISOString().slice(0, 10);
    buckets.set(key, 0);
  }
  for (const a of activities) {
    const key = startOfWeek(a.start_date_local).toISOString().slice(0, 10);
    if (buckets.has(key)) {
      buckets.set(key, buckets.get(key) + a.distance);
    }
  }
  return [...buckets.entries()]
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([week_start, distance_m]) => ({ week_start, distance_m }));
}

async function main() {
  const token = await getAccessToken();
  const athlete = await stravaGet("/athlete", token);
  const stats = await stravaGet(`/athletes/${athlete.id}/stats`, token);
  const activities = await stravaGet("/athlete/activities?per_page=60", token);

  const output = {
    updated_at: new Date().toISOString(),
    athlete: {
      id: athlete.id,
      firstname: athlete.firstname,
      profile_url: `https://www.strava.com/athletes/${athlete.id}`,
    },
    totals: {
      recent_4wk: stats.recent_run_totals || stats.recent_ride_totals,
      ytd: stats.ytd_run_totals || stats.ytd_ride_totals,
      all_time: stats.all_run_totals || stats.all_ride_totals,
    },
    recent_activities: activities.slice(0, 6).map(summarizeActivity),
    weekly_volume: buildWeeklyVolume(activities, 10),
  };

  const fs = await import("node:fs/promises");
  await fs.mkdir("data", { recursive: true });
  await fs.writeFile("data/strava.json", JSON.stringify(output, null, 2) + "\n");
  console.log("wrote data/strava.json");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
