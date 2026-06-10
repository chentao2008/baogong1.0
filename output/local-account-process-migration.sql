--
-- PostgreSQL database dump
--

\restrict sqpg9iqKbnLC6fUdDd3kWnyC9IghejADVWmgtuAercaA7U5FJLCQ0hcchQUBHLW

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

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

--
-- Data for Name: admin_accounts; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.admin_accounts (id, account, password, role, name, status, manager_id, created_at, updated_at, password_view_ciphertext, password_view_updated_at) VALUES ('u-1780385800035', 'zhengdonghang', '$2b$12$NrimIJcIcKYX8nEYgBkxWulzpdFW6i22eJ.3OFHM8JljuDn6DoeMW', 'employee', 'zhengdonghang', 'active', NULL, '2026-06-02 15:36:40.035286+08', '2026-06-08 23:30:05.955811+08', 'gAAAAABqJt_9pOc2Lx2WkaVPFrRgWZBG4kp0M2BnflPiufDsUKNCrw7vYuGIZWhenBnJ-DLTNsBelZ0L7rEGpAIyx9x5yJC92Q==', '2026-06-08 23:30:05.955811+08');
INSERT INTO public.admin_accounts (id, account, password, role, name, status, manager_id, created_at, updated_at, password_view_ciphertext, password_view_updated_at) VALUES ('u-1780729494258', 'zhengdongjie', '$2b$12$VMQyZRqfHwmE2oeUzdsPuOMNSFiiL/QRXJhgXq7TE7nWIrHEirt2m', 'admin', 'zhengdongjie', 'active', NULL, '2026-06-06 15:04:54.255903+08', '2026-06-08 23:30:15.315516+08', 'gAAAAABqJuAHG0bbihkbwM-kUGQ-Y4m2WTPlIu6UeNke4Lu4YJ1r3iCExreapH-t7m-j1nMQ7yJC4Ttmx6dXf9Z5v-zra8vn9Q==', '2026-06-08 23:30:15.315516+08');
INSERT INTO public.admin_accounts (id, account, password, role, name, status, manager_id, created_at, updated_at, password_view_ciphertext, password_view_updated_at) VALUES ('u-1780729988913', 'zhengshu', '$2b$12$hctim5b5G5FYz.E9cyR/ZObgYxuPKE0qy5Wxk3UWLBmhrrZWaMTy6', 'employee', 'zhengshu', 'active', 'u-1780729494258', '2026-06-06 15:13:08.912971+08', '2026-06-08 23:30:26.095627+08', 'gAAAAABqJuAS155Hap8YETnMx6LEbBFhHmfGNLv4D4fh3A3N-s_IWegKpoTSj6zu2vkvV2wIn5ik3mF1C7TkSygrUeIY4l0f_w==', '2026-06-08 23:30:26.095627+08');
INSERT INTO public.admin_accounts (id, account, password, role, name, status, manager_id, created_at, updated_at, password_view_ciphertext, password_view_updated_at) VALUES ('u-1780932883359', 'mingdeyao', '$2b$12$CcQHulYXIoOK0nagj.4YS.R/A7xUhgfipLJqRw4hNNuYqumEu8y1G', 'employee', 'mingdeyao', 'active', 'u-1780494967545', '2026-06-08 23:34:43.348969+08', '2026-06-08 23:34:43.348969+08', 'gAAAAABqJuETWP1hg7fEX7TZAHfiDi7PK_bKb9ZVS8FYBv1m7bDP1LSQRoA9tM8s7sqIR1FP7fC_0iS9r2sC8DhD11IMADkOzw==', '2026-06-08 23:34:43.348969+08');
INSERT INTO public.admin_accounts (id, account, password, role, name, status, manager_id, created_at, updated_at, password_view_ciphertext, password_view_updated_at) VALUES ('u-1780495064441', 'chenyuhan', '$2b$12$/XD87iK52ogr3SCH6c3Wb.tn.Gni6RH9X28/b7nt0iLIr30/8/TkS', 'employee', 'chenyuhan', 'active', 'u-1780494967545', '2026-06-03 21:57:44.442617+08', '2026-06-08 23:27:39.725284+08', 'gAAAAABqJt9rbGqqJ-gMKAnvKlNhuKmzL3kMnzGp8yri_fe1P9aLTnTY0X_sKDTu7XDA65mV6NJEKKmlcNiG25fQKrOpBoPXgw==', '2026-06-08 23:27:39.725284+08');
INSERT INTO public.admin_accounts (id, account, password, role, name, status, manager_id, created_at, updated_at, password_view_ciphertext, password_view_updated_at) VALUES ('u-1780495388962', 'jiangfen', '$2b$12$Zr0X8l0wDZJ/rJ9oaYD1nelCKja7z2/jbJdjpJOQwJv8KW1A5JGHm', 'employee', 'jiangfen', 'active', 'u-1780494967545', '2026-06-03 22:03:08.96294+08', '2026-06-08 23:27:51.952051+08', 'gAAAAABqJt93wvGwFYDh8JsnqlJX8jyMK_zugRCHcPN3QpTdUSAe62upkOYLMfiGWmZJU-K78X1FO949fbmKy1Hz1zNM9RZ6vg==', '2026-06-08 23:27:51.952051+08');
INSERT INTO public.admin_accounts (id, account, password, role, name, status, manager_id, created_at, updated_at, password_view_ciphertext, password_view_updated_at) VALUES ('u-1780730516170', 'huangguangqiao', '$2b$12$CAaZuEAn0vXOvefg3ejsbeu80z7rQvQ50e8tTlwxijWZAsWU.ukVa', 'employee', 'huangguangqiao', 'active', 'u-1780494967545', '2026-06-06 15:21:56.169083+08', '2026-06-08 23:28:02.593402+08', 'gAAAAABqJt-CfeYix_4m-wWBR3CRxJ88CZLqsF-Q_n38PJWMJ2GRSmoiDtvgD35o9-kyZ11R9P6cQH5V7llV0Jx_gXEGslEsMg==', '2026-06-08 23:28:02.593402+08');
INSERT INTO public.admin_accounts (id, account, password, role, name, status, manager_id, created_at, updated_at, password_view_ciphertext, password_view_updated_at) VALUES ('u-1780414325957', 'chentao', '$2b$12$GsDKHc6JpV7t5oeEoiUE9.e3rRmlkeOsPXs196dPRASuuimpsZqZC', 'super_admin', 'chentao', 'active', NULL, '2026-06-02 23:32:05.958406+08', '2026-06-08 23:28:56.128196+08', 'gAAAAABqJt-49vRwIsftPpQLBQIoNs6y8YdzX277zsWB-Obyp4GvfvTMNXVULBRUtdOc9pE4lRrj0OR8JRWZzz9DvN601e-5Mg==', '2026-06-08 23:28:56.128196+08');
INSERT INTO public.admin_accounts (id, account, password, role, name, status, manager_id, created_at, updated_at, password_view_ciphertext, password_view_updated_at) VALUES ('u-1780494967545', 'chenmingchuan', '$2b$12$mNp0sAtwsi8JAYfeiEKMeO/cXcvxGzss49M3jj0sG6bbwsmOQ8K8S', 'admin', 'chenmingchuan', 'active', NULL, '2026-06-03 21:56:07.546558+08', '2026-06-08 23:29:47.703747+08', 'gAAAAABqJt_rVk2yqskN8KaZhXY1hmcH3jnXHmfcBHOD2AqHIteW6NRsZk6bfxfbZnQyG3DX3rXNLnHjpuu2aaqiGYJcoBAZwg==', '2026-06-08 23:29:47.703747+08');


--
-- Data for Name: processes; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780570685110', '四号机', 4.10, '元/千针', 'active', '2026-06-04 18:58:05.110533+08', '2026-06-04 19:08:58.877791+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780570694717', '五号机', 4.10, '元/卷', 'active', '2026-06-04 18:58:14.714523+08', '2026-06-04 19:09:03.96696+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780571359008', '六号机', 4.10, '元/千针', 'active', '2026-06-04 19:09:19.008647+08', '2026-06-04 19:09:19.008647+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780726905304', '打大包', 10.00, '元/大包', 'active', '2026-06-06 14:21:45.292006+08', '2026-06-06 14:21:45.292006+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780726921942', '打小包', 8.00, '元/小包', 'active', '2026-06-06 14:22:01.940383+08', '2026-06-06 14:22:01.940383+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780726934251', '打快递包', 4.00, '元/包', 'active', '2026-06-06 14:22:14.244081+08', '2026-06-06 14:22:14.244081+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780726956203', '发货大包', 10.00, '元/大包', 'active', '2026-06-06 14:22:36.202076+08', '2026-06-06 14:22:36.202076+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780726975240', '发货小包', 7.00, '元/小包', 'active', '2026-06-06 14:22:55.240762+08', '2026-06-06 14:32:04.658547+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780727556843', '送市场', 5.00, '元/包', 'active', '2026-06-06 14:32:36.842735+08', '2026-06-06 14:32:36.842735+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780728216598', '配快递', 6.00, '元/包', 'active', '2026-06-06 14:43:36.591378+08', '2026-06-06 14:43:36.591378+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780728226824', '配货', 12.00, '元/包', 'active', '2026-06-06 14:43:46.823251+08', '2026-06-06 14:43:46.823251+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780728247142', '配客户整卷', 10.00, '元/包', 'active', '2026-06-06 14:44:07.141766+08', '2026-06-06 14:44:07.141766+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494564347', '滚边绳', 1.15, '元/条', 'active', '2026-06-03 21:49:24.347739+08', '2026-06-03 21:49:24.347739+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494584794', '切小条', 24.00, '元/卷', 'active', '2026-06-03 21:49:44.793986+08', '2026-06-03 21:49:44.793986+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494606273', '切寸布', 12.00, '元/卷', 'active', '2026-06-03 21:50:06.273592+08', '2026-06-03 21:50:06.273592+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494621058', '切包边条', 12.00, '元/卷', 'active', '2026-06-03 21:50:21.05797+08', '2026-06-03 21:50:21.05797+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494658491', '卷单布', 6.00, '元/卷', 'active', '2026-06-03 21:50:58.491202+08', '2026-06-03 21:50:58.491202+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494672064', '卷底布', 4.00, '元/卷', 'active', '2026-06-03 21:51:12.065156+08', '2026-06-03 21:51:12.065156+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494693688', '卷火套底布', 8.00, '元/卷', 'active', '2026-06-03 21:51:33.689528+08', '2026-06-03 21:51:33.689528+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494739513', '计时一天', 350.00, '元/天', 'active', '2026-06-03 21:52:19.513404+08', '2026-06-03 21:52:19.513404+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494753698', '计时上午', 150.00, '元/上午', 'active', '2026-06-03 21:52:33.69796+08', '2026-06-03 21:52:33.69796+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780494766858', '计时下午', 200.00, '元/下午', 'active', '2026-06-03 21:52:46.858526+08', '2026-06-03 21:52:46.858526+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780729779401', '打大包', 10.00, '元/包', 'active', '2026-06-06 15:09:39.400315+08', '2026-06-06 15:09:39.400315+08', 'u-1780729494258');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780729794913', '打小包', 8.00, '元/包', 'active', '2026-06-06 15:09:54.912784+08', '2026-06-06 15:09:54.912784+08', 'u-1780729494258');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780729804344', '发大包', 10.00, '元/包', 'active', '2026-06-06 15:10:04.344393+08', '2026-06-06 15:10:04.344393+08', 'u-1780729494258');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780729815240', '发小包', 7.00, '元/包', 'active', '2026-06-06 15:10:15.240192+08', '2026-06-06 15:10:15.240192+08', 'u-1780729494258');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780729826185', '打快递包', 4.00, '元/包', 'active', '2026-06-06 15:10:26.184062+08', '2026-06-06 15:10:26.184062+08', 'u-1780729494258');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780729840489', '打火套', 20.00, '元/包', 'active', '2026-06-06 15:10:40.488661+08', '2026-06-06 15:10:40.488661+08', 'u-1780729494258');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780570638876', '一号机', 4.10, '元/千针', 'active', '2026-06-04 18:57:18.874671+08', '2026-06-04 19:03:26.086142+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780570651025', '二号机', 4.10, '元/千针', 'active', '2026-06-04 18:57:31.024758+08', '2026-06-04 19:03:31.055731+08', NULL);
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780729956592', '送市场', 5.00, '元/包', 'active', '2026-06-06 15:12:36.592603+08', '2026-06-06 15:12:36.592603+08', 'u-1780729494258');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780730116057', '1号机', 4.10, '元/千针', 'active', '2026-06-06 15:15:16.056674+08', '2026-06-06 15:15:16.056674+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780730127161', '2号机', 4.10, '元/千针', 'active', '2026-06-06 15:15:27.161022+08', '2026-06-06 15:15:27.161022+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780730147060', '3号机', 3.20, '元/千针', 'active', '2026-06-06 15:15:47.0591+08', '2026-06-06 15:15:47.0591+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780730176634', '四号机', 4.10, '元/千针', 'active', '2026-06-06 15:16:16.632685+08', '2026-06-06 15:16:16.632685+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780730187785', '五号机', 4.10, '元/千针', 'active', '2026-06-06 15:16:27.784589+08', '2026-06-06 15:16:27.784589+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780730203009', '六号机', 4.10, '元/千针', 'active', '2026-06-06 15:16:43.008623+08', '2026-06-06 15:16:43.008623+08', 'u-1780494967545');
INSERT INTO public.processes (id, name, price, unit, status, created_at, updated_at, manager_id) VALUES ('p-1780570664731', '三号机', 3.20, '元/千针', 'active', '2026-06-04 18:57:44.731571+08', '2026-06-04 19:03:39.150724+08', NULL);


--
-- Data for Name: account_processes; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780495064441', 'p-1780494739513');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494584794');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780729494258', 'p-1780728247142');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494564347');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494584794');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494606273');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494621058');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494658491');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780495388962', 'p-1780494739513');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494672064');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494693688');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494739513');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494753698');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780932883359', 'p-1780494766858');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780730516170', 'p-1780730116057');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780730516170', 'p-1780730127161');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780730516170', 'p-1780730147060');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780730516170', 'p-1780730176634');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494564347');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494584794');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494606273');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494621058');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494658491');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494672064');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494693688');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494739513');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494753698');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780385800035', 'p-1780494766858');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780730516170', 'p-1780730187785');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780730516170', 'p-1780730203009');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780729988913', 'p-1780729779401');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780729988913', 'p-1780729794913');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780729988913', 'p-1780729804344');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780729988913', 'p-1780729815240');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780729988913', 'p-1780729826185');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780729988913', 'p-1780729840489');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780729988913', 'p-1780729956592');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494564347');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494584794');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494606273');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494621058');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494658491');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494672064');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494693688');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494739513');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494753698');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780414325957', 'p-1780494766858');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494564347');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494606273');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494621058');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494658491');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494672064');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494693688');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494739513');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494753698');
INSERT INTO public.account_processes (account_id, process_id) VALUES ('u-1780494967545', 'p-1780494766858');


--
-- PostgreSQL database dump complete
--

\unrestrict sqpg9iqKbnLC6fUdDd3kWnyC9IghejADVWmgtuAercaA7U5FJLCQ0hcchQUBHLW

