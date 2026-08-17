                # ==================================================
                # NEXT RUN
                # فقط آخرین پیام کانال
                # ==================================================

                last_id = int(saved_last_id)

                print(
                    f"[TG] Checking latest message | "
                    f"channel={channel} | "
                    f"last_id={last_id}",
                    flush=True,
                )

                # فقط آخرین پیام کانال
                latest = await client.get_messages(
                    entity,
                    limit=1,
                )

                if not latest:
                    print(
                        f"[TG] No messages: {channel}",
                        flush=True,
                    )
                    continue

                message = latest[0]

                if not message or not message.id:
                    continue

                latest_id = message.id

                print(
                    f"[TG] Latest message ID: {latest_id}",
                    flush=True,
                )

                # پیام جدیدی منتشر نشده
                if latest_id <= last_id:
                    print(
                        f"[TG] No new message: {channel}",
                        flush=True,
                    )
                    continue

                # فقط همین یک پیام جدید
                text = get_full_message_text(message)

                found_configs = 0

                if text:
                    configs = extract_configs(text)

                    found_configs = len(configs)

                    for config in configs:
                        collected.append({
                            "config": config,
                            "source": channel,
                            "message_id": message.id,
                        })

                # آخرین پیام ثبت می‌شود
                telegram_state[key] = latest_id

                print(
                    f"[TG] NEW MESSAGE PROCESSED | "
                    f"channel={channel} | "
                    f"message_id={latest_id} | "
                    f"configs={found_configs}",
                    flush=True,
                )
