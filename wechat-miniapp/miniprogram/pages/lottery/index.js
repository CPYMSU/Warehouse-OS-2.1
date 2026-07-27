const member = require('../../services/member');
const context = require('../../services/context');
const pending = require('../../store/pending');
const companyUtil = require('../../utils/company');
const time = require('../../utils/time');

function campaignRow(campaign) {
  const available = Boolean(campaign.available);
  const drawsRemaining = Number(campaign.draws_remaining || 0);
  return {
    ...campaign,
    available,
    endsLocal: time.formatLocalDateTime(campaign.ends_at),
    remainingLabel: `${campaign.draws_remaining}/${campaign.max_draws_per_member}`,
    buttonLabel: available
      ? '由服务器安全开奖'
      : (drawsRemaining <= 0 ? '本活动次数已用完' : '活动暂不可抽'),
  };
}

function rewardStatus(status) {
  return ({ issued: '待核销', redeemed: '已核销', expired: '已过期', revoked: '已撤销' })[status] || status;
}

function rewardRow(reward) {
  return {
    ...reward,
    statusLabel: rewardStatus(reward.status),
    issuedLocal: time.formatLocalDateTime(reward.issued_at),
  };
}

Page({
  drawInFlight: false,
  data: {
    campaigns: [],
    selectedCampaignCode: '',
    selectedCampaign: null,
    rewards: [],
    contextLoading: true,
    companyCode: '',
    companyName: '',
    companyMode: '',
    busy: false,
    error: '',
    result: null,
  },
  onShow() { this.loadContext(); },
  async loadContext() {
    try {
      this.setData({ contextLoading: true, error: '' });
      const selected = await context.requireCompany();
      if (!selected) {
        this.setData({
          contextLoading: false,
          companyCode: '',
          companyName: '',
          companyMode: '',
          campaigns: [],
          selectedCampaign: null,
          selectedCampaignCode: '',
          rewards: [],
          result: null,
        });
        return;
      }
      const [campaignResult, rewardResult] = await Promise.all([
        member.lotteryCampaigns(selected.code),
        member.rewards(selected.code),
      ]);
      const campaigns = (campaignResult.campaigns || []).map(campaignRow);
      const companyChanged = Boolean(
        this.data.companyCode && this.data.companyCode !== selected.code,
      );
      const previous = companyChanged ? '' : this.data.selectedCampaignCode;
      const selectedCampaign = campaigns.find((item) => item.campaign_code === previous)
        || campaigns.find((item) => item.available)
        || campaigns[0]
        || null;
      this.setData({
        contextLoading: false,
        companyCode: selected.code,
        companyName: selected.company.name,
        companyMode: companyUtil.modeLabel(selected.company),
        campaigns,
        selectedCampaign,
        selectedCampaignCode: selectedCampaign ? selectedCampaign.campaign_code : '',
        rewards: (rewardResult.rewards || []).map(rewardRow),
        result: companyChanged ? null : this.data.result,
        error: '',
      });
    } catch (error) {
      this.setData({
        contextLoading: false,
        companyCode: '',
        companyName: '',
        companyMode: '',
        campaigns: [],
        selectedCampaign: null,
        selectedCampaignCode: '',
        rewards: [],
        result: null,
        error: error.message || '无法读取抽奖活动',
      });
    }
  },
  chooseCampaign(event) {
    const code = event.currentTarget.dataset.code;
    const selectedCampaign = this.data.campaigns.find((item) => item.campaign_code === code) || null;
    this.setData({ selectedCampaignCode: code, selectedCampaign, result: null, error: '' });
  },
  async draw() {
    const companyCode = this.data.companyCode;
    const campaign = this.data.selectedCampaign;
    if (!companyCode || !campaign || !campaign.available || this.drawInFlight) return;
    this.drawInFlight = true;
    const campaignCode = campaign.campaign_code;
    const scope = `${companyCode}:${campaignCode}`;
    let requestId = pending.get('lottery-draw', scope);
    try {
      this.setData({ busy: true, error: '', result: null });
      if (!requestId) {
        requestId = await member.newRequestId('draw');
        pending.set('lottery-draw', scope, requestId);
      }
      const result = await member.draw(companyCode, campaignCode, requestId);
      pending.clear('lottery-draw', scope);
      this.setData({ result });
      await this.loadContext();
    } catch (error) {
      this.setData({ error: error.message || '开奖结果暂不确定，请点击重试' });
    } finally {
      this.drawInFlight = false;
      this.setData({ busy: false });
    }
  },
});
