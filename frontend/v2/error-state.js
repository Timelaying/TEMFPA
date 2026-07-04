/**
 * Renders an error banner with a dismiss button.
 */

const ERROR_MESSAGES = {
  '404': 'The requested team or league could not be found.',
  '422': 'Invalid request. Please check your input.',
  '500': 'An internal server error occurred. Please try again later.',
  'NETWORK_ERROR': 'Unable to connect to the TEMFPA server. Please check that the API is running.',
  DEFAULT: 'An unexpected error occurred. Please try again.',
};

export function renderError(error, container) {
  if (!error) {
    container.style.display = 'none';
    container.innerHTML = '';
    return;
  }

  const message = ERROR_MESSAGES[error.code] || error.error || ERROR_MESSAGES.DEFAULT;
  const details = error.details ? `<p class="v2-error-details">${error.details}</p>` : '';

  container.style.display = 'block';
  container.innerHTML = `
    <div class="v2-error-banner" role="alert" aria-live="assertive">
      <div class="v2-error-content">
        <svg class="v2-error-icon" viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 8v4m0 4h.01"/>
        </svg>
        <div>
          <strong class="v2-error-title">Prediction failed</strong>
          <p class="v2-error-message">${message}</p>
          ${details}
        </div>
      </div>
      <button class="v2-error-dismiss" type="button" aria-label="Dismiss error">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M6 6l8 8M6 14L14 6"/></svg>
      </button>
    </div>
  `;

  const dismissBtn = container.querySelector('.v2-error-dismiss');
  if (dismissBtn) {
    dismissBtn.addEventListener('click', () => {
      container.style.display = 'none';
      container.innerHTML = '';
    });
  }
}
