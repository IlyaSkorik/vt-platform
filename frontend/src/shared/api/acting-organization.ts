/**
 * Которую организацию оператор платформы сейчас ведёт.
 *
 * Поддержка работает изнутри панели: «у вас не принимаются заявки» разбирают,
 * открыв кабинет организатора, а не читая базу через плечо. Оператор выбирает
 * организацию в консоли, и с этого момента каждый запрос уходит с заголовком
 * `X-Acting-Organization` — сервер его читает только у оператора платформы, для
 * всех остальных такого заголовка просто нет (apps/organization/presentation/scope.py).
 *
 * В `localStorage`, а не в памяти, и этим отличается от `tokenStore`: токен там
 * не хранят, потому что это ключ, а это — не ключ, а ответ на вопрос «что я
 * сейчас смотрю». Переживает F5, иначе перезагрузка страницы молча выбрасывала
 * бы оператора из кабинета в середине разбора.
 *
 * Имя организации лежит рядом с её id, чтобы баннер «вы в кабинете X» рисовался
 * сразу, без ещё одного запроса и без пустого места на его время.
 */

export type ActingOrganization = {
  id: string;
  name: string;
};

const STORAGE_KEY = "vt.acting-organization";

function read(): ActingOrganization | null {
  if (typeof localStorage === "undefined") {
    return null;
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw == null) {
      return null;
    }
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) {
      return null;
    }
    const { id, name } = parsed as Partial<ActingOrganization>;
    return typeof id === "string" && id !== "" && typeof name === "string" ? { id, name } : null;
  } catch {
    // Испорченная запись — это не состояние, в котором стоит падать: оператор
    // просто оказывается вне кабинета, что и так верный ответ по умолчанию.
    return null;
  }
}

let current: ActingOrganization | null = read();
const listeners = new Set<() => void>();

export const actingOrganizationStore = {
  /** Организация, внутри которой оператор сейчас работает, или `null`. */
  get(): ActingOrganization | null {
    return current;
  },
  /** Войти в кабинет организации (или выйти из него, передав `null`). */
  set(value: ActingOrganization | null): void {
    current = value;
    if (typeof localStorage !== "undefined") {
      if (value === null) {
        localStorage.removeItem(STORAGE_KEY);
      } else {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
      }
    }
    for (const listener of listeners) {
      listener();
    }
  },
  /** Подписка для `useSyncExternalStore`. */
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
};

export type ActingOrganizationStore = typeof actingOrganizationStore;
