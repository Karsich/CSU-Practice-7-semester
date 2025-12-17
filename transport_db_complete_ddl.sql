--
-- PostgreSQL database dump
--

-- Dumped from database version 15.13
-- Dumped by pg_dump version 15.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.load_data DROP CONSTRAINT IF EXISTS load_data_stop_id_fkey;
ALTER TABLE IF EXISTS ONLY public.forecasts DROP CONSTRAINT IF EXISTS forecasts_stop_id_fkey;
ALTER TABLE IF EXISTS ONLY public.bus_detections DROP CONSTRAINT IF EXISTS bus_detections_stop_id_fkey;
DROP INDEX IF EXISTS public.ix_stops_id;
DROP INDEX IF EXISTS public.ix_load_data_timestamp;
DROP INDEX IF EXISTS public.ix_load_data_id;
DROP INDEX IF EXISTS public.ix_forecasts_id;
DROP INDEX IF EXISTS public.ix_forecasts_forecast_time;
DROP INDEX IF EXISTS public.ix_bus_detections_id;
DROP INDEX IF EXISTS public.ix_bus_detections_detected_at;
ALTER TABLE IF EXISTS ONLY public.stops DROP CONSTRAINT IF EXISTS stops_pkey;
ALTER TABLE IF EXISTS ONLY public.load_data DROP CONSTRAINT IF EXISTS load_data_pkey;
ALTER TABLE IF EXISTS ONLY public.forecasts DROP CONSTRAINT IF EXISTS forecasts_pkey;
ALTER TABLE IF EXISTS ONLY public.bus_detections DROP CONSTRAINT IF EXISTS bus_detections_pkey;
ALTER TABLE IF EXISTS public.stops ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.load_data ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.forecasts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.bus_detections ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.stops_id_seq;
DROP TABLE IF EXISTS public.stops;
DROP SEQUENCE IF EXISTS public.load_data_id_seq;
DROP TABLE IF EXISTS public.load_data;
DROP SEQUENCE IF EXISTS public.forecasts_id_seq;
DROP TABLE IF EXISTS public.forecasts;
DROP SEQUENCE IF EXISTS public.bus_detections_id_seq;
DROP TABLE IF EXISTS public.bus_detections;
DROP EXTENSION IF EXISTS timescaledb;
--
-- Name: timescaledb; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS timescaledb WITH SCHEMA public;


--
-- Name: EXTENSION timescaledb; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION timescaledb IS 'Enables scalable inserts and complex queries for time-series data (Community Edition)';


SET default_table_access_method = heap;

--
-- Name: bus_detections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bus_detections (
    id integer NOT NULL,
    stop_id integer NOT NULL,
    bus_number character varying(50),
    detected_at timestamp with time zone DEFAULT now(),
    confidence double precision,
    bus_bbox json,
    detection_data json
);


--
-- Name: bus_detections_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.bus_detections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: bus_detections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.bus_detections_id_seq OWNED BY public.bus_detections.id;


--
-- Name: forecasts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.forecasts (
    id integer NOT NULL,
    stop_id integer NOT NULL,
    forecast_time timestamp with time zone NOT NULL,
    predicted_people_count double precision NOT NULL,
    confidence_interval_lower double precision,
    confidence_interval_upper double precision,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: forecasts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.forecasts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: forecasts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.forecasts_id_seq OWNED BY public.forecasts.id;


--
-- Name: load_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.load_data (
    id integer NOT NULL,
    stop_id integer NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    people_count integer,
    buses_detected integer,
    detection_data json
);


--
-- Name: load_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.load_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: load_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.load_data_id_seq OWNED BY public.load_data.id;


--
-- Name: stops; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stops (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    camera_id character varying(100),
    camera_url character varying(500),
    yandex_map_url character varying(500),
    stop_zone_coords json,
    original_resolution json,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: stops_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.stops_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stops_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.stops_id_seq OWNED BY public.stops.id;


--
-- Name: bus_detections id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bus_detections ALTER COLUMN id SET DEFAULT nextval('public.bus_detections_id_seq'::regclass);


--
-- Name: forecasts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.forecasts ALTER COLUMN id SET DEFAULT nextval('public.forecasts_id_seq'::regclass);


--
-- Name: load_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.load_data ALTER COLUMN id SET DEFAULT nextval('public.load_data_id_seq'::regclass);


--
-- Name: stops id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stops ALTER COLUMN id SET DEFAULT nextval('public.stops_id_seq'::regclass);


--
-- Name: bus_detections bus_detections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bus_detections
    ADD CONSTRAINT bus_detections_pkey PRIMARY KEY (id);


--
-- Name: forecasts forecasts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.forecasts
    ADD CONSTRAINT forecasts_pkey PRIMARY KEY (id);


--
-- Name: load_data load_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.load_data
    ADD CONSTRAINT load_data_pkey PRIMARY KEY (id);


--
-- Name: stops stops_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stops
    ADD CONSTRAINT stops_pkey PRIMARY KEY (id);


--
-- Name: ix_bus_detections_detected_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bus_detections_detected_at ON public.bus_detections USING btree (detected_at);


--
-- Name: ix_bus_detections_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bus_detections_id ON public.bus_detections USING btree (id);


--
-- Name: ix_forecasts_forecast_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_forecasts_forecast_time ON public.forecasts USING btree (forecast_time);


--
-- Name: ix_forecasts_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_forecasts_id ON public.forecasts USING btree (id);


--
-- Name: ix_load_data_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_load_data_id ON public.load_data USING btree (id);


--
-- Name: ix_load_data_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_load_data_timestamp ON public.load_data USING btree ("timestamp");


--
-- Name: ix_stops_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_stops_id ON public.stops USING btree (id);


--
-- Name: bus_detections bus_detections_stop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bus_detections
    ADD CONSTRAINT bus_detections_stop_id_fkey FOREIGN KEY (stop_id) REFERENCES public.stops(id);


--
-- Name: forecasts forecasts_stop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.forecasts
    ADD CONSTRAINT forecasts_stop_id_fkey FOREIGN KEY (stop_id) REFERENCES public.stops(id);


--
-- Name: load_data load_data_stop_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.load_data
    ADD CONSTRAINT load_data_stop_id_fkey FOREIGN KEY (stop_id) REFERENCES public.stops(id);


--
-- PostgreSQL database dump complete
--

