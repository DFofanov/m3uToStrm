# m3uToStrm

## Скрипт импорта медиаконтента из файла m3u для медиакомбайна Emby (https://emby.media/)

[<img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=float&logo=python&logoColor=white" />](https://www.python.org/)

Подробно формат файлов описан в WIKI Emby (https://support.emby.media/support/solutions/articles/44001159179-theme-songs-videos)

<img src="https://emby.media/resources/msg-3-0-39164600-1443639466.png">

### Основные функции скриптра

* Создание структуры папок согластно спецификации Emby
* Получение информации с порталов tmdb3 и kinopoisk_api
* Загрузка постеров и задников
* Создание файла NFO (https://en.wikipedia.org/wiki/.nfo)
* Проверка медиаконтента на работоспособность

### Структура папок
* Год выпуска
   * Название медиаконтента (Год выпуска)
      * Название медиаконтента (Год выпуска) - Качество [ Поставщик контента ] . STRM
      * Название медиаконтента (Год выпуска) - Качество [ Поставщик контента ] . NFO
      * Постер . JPG
      * Задник . JPG

### Параметры

| Параметр | Описание |
|:---------|:----------------------------------|
| directory | Рабочая папка |
| m3u_file | Название M3U файла |
| provider_prifix | Поставщик контента |
| path_name | Папка в которой создаеться медиаконтент |
| kinopoisk_key | Токен API KINOPOISK |

## Лицензия
Licensed under the GPL-3.0 License.