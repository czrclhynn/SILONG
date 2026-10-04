CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS datasets (
 id text PRIMARY KEY, provenance text NOT NULL CHECK (provenance IN ('synthetic','observed','reanalysis')),
 source_url text, imported_at timestamptz NOT NULL DEFAULT now(), quality jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS locations (
 city_id text PRIMARY KEY, name text NOT NULL, boundary geometry(MultiPolygon,4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS locations_boundary_idx ON locations USING gist(boundary);
CREATE TABLE IF NOT EXISTS observations (
 dataset_id text REFERENCES datasets(id), city_id text REFERENCES locations(city_id),
 timestamp timestamptz NOT NULL, temperature double precision CHECK (temperature BETWEEN 10 AND 50),
 humidity double precision CHECK (humidity BETWEEN 0 AND 100), heat_index double precision,
 source_heat_index double precision, outlier_flag boolean DEFAULT false,
 PRIMARY KEY (dataset_id,city_id,timestamp)
);
CREATE INDEX IF NOT EXISTS observations_time_idx ON observations(timestamp);
CREATE TABLE IF NOT EXISTS model_versions (
 version text PRIMARY KEY, dataset_id text REFERENCES datasets(id), trained_at timestamptz NOT NULL,
 features jsonb NOT NULL, metrics jsonb NOT NULL, artifact_path text NOT NULL
);
