import { readFileSync, writeFileSync } from "node:fs";

const file = readFileSync("./data/raw_api_data.json");
const data = JSON.parse(file.toString())
const playlists = data.filter(d => d.tracks.length > 0);
const output = playlists.map(({ name, cover, tracks }) => {
  const dates = tracks.map(s => new Date(s.added_at));
  const date = new Date(Math.min(...dates));
  const valence = tracks.map(s => s.valence).reduce((sum, accumulator) => sum + accumulator, 0) / tracks.length;
  return ({ name, cover, valence, date, tracks })
});

writeFileSync("./data/data.json", JSON.stringify(output));
