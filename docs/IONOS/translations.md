# Translations

## Rules

* Add texts in English to the source code
* For custom components in `src/lib/IONOS/`: use the namespace `ionos` (`{$i18n.t('Some text', { ns: 'ionos' })}`)


## Process overview

Translations are a five step process:

1. Parse source code for keys
2. Commit `ionos.json`s to Git with a message like "regenerate locales" and how it was regenerated in the commit message body
3. Upload `src/lib/i18n/locales/en-US/ionos.json` to translation management
4. Have translators translate/update texts
5. Download `src/lib/i18n/locales/{en-US,de-DE}/ionos.json` from  translation management

### Parse

```
container $ npm run i18n:parse
```

This will parse translation queries from the source and write the strings to `src/lib/i18n/locales/`. This will update a lot files, yet we're only interested in `.../en-US/ionos.json`.

### Upload to translation management

The `ionos.json` can directly be uploaded. Use the file type "i18next".

### Download from translation management

Place the "en" and "de" downloads as `ionos.json` in the respective locale folders `en-US` and `de-DE`.
