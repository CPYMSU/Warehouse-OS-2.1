'use strict';

const theme = require('../../utils/theme');

Component({
  options: { styleIsolation: 'apply-shared' },
  data: { themeStyle: theme.style(theme.current()) },
  lifetimes: {
    attached() { this.refresh(); },
  },
  pageLifetimes: {
    show() { this.refresh(); },
  },
  methods: {
    refresh() {
      const selected = theme.current();
      this.setData({ themeStyle: theme.style(selected) });
      theme.applyChrome(selected);
    },
  },
});
