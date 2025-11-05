#!/usr/bin/env python3
import os
import sys
import csv
import subprocess
from datetime import datetime
from urllib.parse import urlparse


APP_NAME = "contextquiz-openwebui-kidsgpt"


def get_database_url() -> str | None:
    try:
        result = subprocess.run(
            ["heroku", "config:get", "DATABASE_URL", "-a", APP_NAME],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting DATABASE_URL: {e}", file=sys.stderr)
        return None


def ensure_psycopg2() -> bool:
    try:
        import psycopg2  # noqa: F401
        return True
    except Exception:
        print("Installing psycopg2-binary ...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "psycopg2-binary"],
                check=True,
                capture_output=True,
            )
            import psycopg2  # noqa: F401
            return True
        except Exception as e:
            print(f"Failed to install psycopg2-binary: {e}", file=sys.stderr)
            return False


def open_connection(db_url):
    import psycopg2

    parsed = urlparse(db_url)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        database=parsed.path[1:],
        user=parsed.username,
        password=parsed.password,
        sslmode="require",
    )


def export_query_to_csv(conn, query: str, output_path: str) -> int:
    total_rows = 0
    with conn.cursor() as cur:
        cur.execute(query)
        headers = [desc[0] for desc in cur.description]
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            batch_size = 1000
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                writer.writerows(rows)
                total_rows += len(rows)
                print(f"Processed {total_rows} rows for {os.path.basename(output_path)} ...")
    return total_rows


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    print("Conda env: please run `conda activate open-webui` before executing this script.")

    # Sanity checks: Heroku CLI and auth
    try:
        subprocess.run(["heroku", "--version"], capture_output=True, check=True)
    except Exception:
        print("Heroku CLI not found. Install it and login first.", file=sys.stderr)
        sys.exit(1)
    try:
        subprocess.run(["heroku", "auth:whoami"], capture_output=True, check=True)
    except Exception:
        print("Not logged into Heroku CLI. Run `heroku login`.", file=sys.stderr)
        sys.exit(1)

    db_url = get_database_url()
    if not db_url:
        sys.exit(1)
    if not ensure_psycopg2():
        sys.exit(1)

    try:
        conn = open_connection(db_url)
    except Exception as e:
        print(f"Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)

    t = timestamp()
    child_csv = f"child_profiles_export_{t}.csv"
    mod_csv = f"moderation_sessions_export_{t}.csv"
    exit_csv = f"exit_quiz_responses_export_{t}.csv"

    child_query = """
        SELECT
            cp.id,
            cp.user_id,
            cp.name,
            cp.child_age,
            cp.child_gender,
            cp.child_characteristics,
            cp.parenting_style,
            cp.is_only_child,
            cp.child_has_ai_use,
            cp.child_ai_use_contexts::text,
            cp.parent_llm_monitoring_level,
            cp.attempt_number,
            cp.is_current,
            cp.session_number,
            cp.created_at,
            cp.updated_at,
            u.name AS user_name,
            u.email AS user_email,
            u.role AS user_role,
            u.prolific_pid,
            u.session_number AS user_session_number,
            u.consent_given
        FROM child_profile cp
        LEFT JOIN "user" u ON cp.user_id = u.id
        ORDER BY cp.user_id, cp.created_at;
    """

    mod_query = """
        SELECT 
            ms.id,
            ms.user_id,
            ms.child_id,
            ms.scenario_index,
            ms.attempt_number,
            ms.version_number,
            ms.session_number,
            ms.scenario_prompt,
            ms.original_response,
            ms.initial_decision,
            ms.is_final_version,
            ms.strategies::text,
            ms.custom_instructions::text,
            ms.highlighted_texts::text,
            ms.refactored_response,
            ms.session_metadata::text,
            ms.is_attention_check,
            ms.attention_check_selected,
            ms.attention_check_passed,
            ms.created_at,
            ms.updated_at,
            u.name AS user_name,
            u.email AS user_email,
            u.role AS user_role,
            u.prolific_pid,
            cp.name AS child_name,
            cp.child_age,
            cp.child_gender,
            cp.child_characteristics,
            cp.parenting_style
        FROM moderation_session ms
        LEFT JOIN "user" u ON ms.user_id = u.id
        LEFT JOIN child_profile cp ON ms.child_id = cp.id
        ORDER BY ms.user_id, ms.child_id, ms.scenario_index, ms.attempt_number, ms.version_number;
    """

    exit_query = """
        SELECT
            eq.id,
            eq.user_id,
            eq.child_id,
            eq.answers::text,
            eq.score::text,
            eq.meta::text,
            eq.attempt_number,
            eq.is_current,
            eq.created_at,
            eq.updated_at,
            u.name AS user_name,
            u.email AS user_email,
            u.role AS user_role,
            u.prolific_pid,
            cp.name AS child_name,
            cp.child_age,
            cp.child_gender
        FROM exit_quiz_response eq
        LEFT JOIN "user" u ON eq.user_id = u.id
        LEFT JOIN child_profile cp ON eq.child_id = cp.id
        ORDER BY eq.user_id, eq.child_id, eq.created_at;
    """

    try:
        print(f"Exporting child profiles -> {child_csv}")
        child_rows = export_query_to_csv(conn, child_query, child_csv)
        print(f"Child profiles rows: {child_rows}")

        print(f"Exporting moderation sessions -> {mod_csv}")
        mod_rows = export_query_to_csv(conn, mod_query, mod_csv)
        print(f"Moderation session rows: {mod_rows}")

        print(f"Exporting exit quiz responses -> {exit_csv}")
        exit_rows = export_query_to_csv(conn, exit_query, exit_csv)
        print(f"Exit quiz response rows: {exit_rows}")

        print("Done.")
        print(f"Outputs:\n- {child_csv}\n- {mod_csv}\n- {exit_csv}")
    except Exception as e:
        print(f"Export failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()



